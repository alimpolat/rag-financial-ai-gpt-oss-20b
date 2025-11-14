"""
Authentication routes for JWT-based authentication.
Handles login, token refresh, and user management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timezone
import uuid

from core.auth import (
    AuthService, User, UserCredentials, Token, TokenData,
    get_current_user, get_current_user_optional,
    require_roles, check_rate_limit
)
from core.logging import get_logger
from core.events import publish_event, UserLoginEvent, UserLogoutEvent

logger = get_logger("auth_routes")
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Temporary in-memory user store (replace with database in production)
users_db = {}


@router.get("/test-token", response_model=Token)
async def get_test_token():
    """
    Get a test token for development (REMOVE IN PRODUCTION).
    """
    from core.config import settings
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test token endpoint is disabled in production"
        )
    
    # Create a test user token
    test_user = User(
        user_id="test-user-001",
        email="test@example.com",
        roles=["user", "admin"],
        is_active=True
    )
    
    token = AuthService.create_tokens(test_user)
    logger.info(f"Test token created for development")
    
    return token


class UserRegistration(BaseModel):
    """User registration model."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""
    user_id: str
    email: EmailStr
    full_name: Optional[str]
    roles: list[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class PasswordChange(BaseModel):
    """Password change request model."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordReset(BaseModel):
    """Password reset request model."""
    email: EmailStr


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    registration: UserRegistration,
    current_user: Optional[TokenData] = Depends(get_current_user_optional)
):
    """
    Register a new user.
    
    Public endpoint for user self-registration.
    If authenticated as admin, can assign roles.
    """
    # Check if email already exists
    if any(u.email == registration.email for u in users_db.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = AuthService.get_password_hash(registration.password)
    
    # Determine roles
    roles = ["user"]  # Default role
    if current_user and "admin" in current_user.roles:
        # Admin can create other admins
        roles = ["admin", "user"]
    
    user = User(
        user_id=user_id,
        email=registration.email,
        full_name=registration.full_name,
        roles=roles,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    
    # Store user (in production, save to database)
    users_db[user_id] = {
        "user": user,
        "password_hash": hashed_password
    }
    
    logger.info(f"New user registered: {user.email}")
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserCredentials):
    """
    Login with email and password.
    
    Returns access and refresh tokens.
    """
    # Find user by email (in production, query database)
    user_data = None
    for uid, data in users_db.items():
        if data["user"].email == credentials.email:
            user_data = data
            break
    
    if not user_data:
        # Create default admin user on first login attempt
        if credentials.email == "admin@financial-ai.com" and not users_db:
            # Bootstrap admin user
            user_id = str(uuid.uuid4())
            user = User(
                user_id=user_id,
                email=credentials.email,
                full_name="System Administrator",
                roles=["admin", "user"],
                is_active=True
            )
            users_db[user_id] = {
                "user": user,
                "password_hash": AuthService.get_password_hash("admin123456")
            }
            user_data = users_db[user_id]
            logger.info("Bootstrap admin user created")
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Verify password
    if not AuthService.verify_password(
        credentials.password,
        user_data["password_hash"]
    ):
        logger.warning(f"Failed login attempt for: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    user = user_data["user"]
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    
    # Create tokens
    tokens = AuthService.create_tokens(user)
    
    # Publish login event
    await publish_event(UserLoginEvent(
        user_id=user.user_id,
        email=user.email,
        ip_address="127.0.0.1"  # In production, get from request
    ))
    
    logger.info(f"User logged in: {user.email}")
    
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True)
):
    """
    Refresh access token using refresh token.
    
    Returns new access token and same refresh token.
    """
    try:
        tokens = await AuthService.refresh_access_token(refresh_token)
        logger.debug("Access token refreshed")
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Logout current user.
    
    In production, invalidate tokens in cache/database.
    """
    # Publish logout event
    await publish_event(UserLogoutEvent(
        user_id=current_user.user_id,
        email=current_user.email
    ))
    
    logger.info(f"User logged out: {current_user.email}")
    
    # In production, add token to blacklist
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get current user information.
    
    Requires authentication.
    """
    # Get full user data (in production, query database)
    user_data = users_db.get(current_user.user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = user_data["user"]
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.put("/me/password")
async def change_password(
    password_change: PasswordChange,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Change current user's password.
    
    Requires authentication.
    """
    # Get user data
    user_data = users_db.get(current_user.user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not AuthService.verify_password(
        password_change.current_password,
        user_data["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current password"
        )
    
    # Update password
    user_data["password_hash"] = AuthService.get_password_hash(
        password_change.new_password
    )
    
    logger.info(f"Password changed for user: {current_user.email}")
    
    return {"message": "Password successfully changed"}


@router.post("/reset-password")
async def request_password_reset(
    reset_request: PasswordReset
):
    """
    Request password reset.
    
    Sends reset link to email (in production).
    """
    # Check if user exists
    user_exists = any(
        u.email == reset_request.email
        for u in (data["user"] for data in users_db.values())
    )
    
    # Always return success to prevent email enumeration
    if user_exists:
        # In production, send reset email with token
        logger.info(f"Password reset requested for: {reset_request.email}")
    
    return {
        "message": "If the email exists, a password reset link has been sent"
    }


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: TokenData = Depends(require_roles("admin")),
    skip: int = 0,
    limit: int = 100
):
    """
    List all users (admin only).
    
    Requires admin role.
    """
    users = []
    for user_data in list(users_db.values())[skip:skip + limit]:
        user = user_data["user"]
        users.append(UserResponse(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            roles=user.roles,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        ))
    
    return users


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: TokenData = Depends(require_roles("admin"))
):
    """
    Activate a user account (admin only).
    
    Requires admin role.
    """
    user_data = users_db.get(user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_data["user"].is_active = True
    logger.info(f"User activated: {user_data['user'].email} by admin: {current_user.email}")
    
    return {"message": "User activated successfully"}


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: TokenData = Depends(require_roles("admin"))
):
    """
    Deactivate a user account (admin only).
    
    Requires admin role.
    """
    user_data = users_db.get(user_id)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deactivation
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user_data["user"].is_active = False
    logger.info(f"User deactivated: {user_data['user'].email} by admin: {current_user.email}")
    
    return {"message": "User deactivated successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: TokenData = Depends(require_roles("admin"))
):
    """
    Delete a user account (admin only).
    
    Requires admin role.
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user_email = users_db[user_id]["user"].email
    del users_db[user_id]
    
    logger.info(f"User deleted: {user_email} by admin: {current_user.email}")
    
    return {"message": "User deleted successfully"}


@router.get("/verify")
async def verify_token(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Verify if current token is valid.
    
    Useful for frontend token validation.
    """
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "email": current_user.email,
        "roles": current_user.roles
    }


@router.post("/rate-limit-test")
async def test_rate_limit(
    current_user: TokenData = Depends(check_rate_limit)
):
    """
    Test endpoint for rate limiting.
    
    Limited to 100 requests per minute per user.
    """
    return {
        "message": "Request successful",
        "user_id": current_user.user_id
    }