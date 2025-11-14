"""
JWT Authentication and Authorization module.
Implements secure authentication with access and refresh tokens.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
import secrets
import logging

from core.config import settings
from core.logging import get_logger

logger = get_logger("auth")

# Security configurations
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT Settings
SECRET_KEY = settings.SECRET_KEY or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = 7


class TokenData(BaseModel):
    """Token data model."""
    user_id: str
    email: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    exp: Optional[datetime] = None


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCredentials(BaseModel):
    """User credentials for login."""
    email: EmailStr
    password: str


class User(BaseModel):
    """User model."""
    user_id: str
    email: EmailStr
    full_name: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None


class AuthService:
    """Authentication service for JWT token management."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        logger.debug(f"Created access token for user: {data.get('sub')}")
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        logger.debug(f"Created refresh token for user: {data.get('sub')}")
        return encoded_jwt
    
    @staticmethod
    def create_tokens(user: User) -> Token:
        """
        Create both access and refresh tokens for a user.
        
        Args:
            user: User object
            
        Returns:
            Token object with both tokens
        """
        token_data = {
            "sub": user.user_id,
            "email": user.email,
            "roles": user.roles
        }
        
        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    @staticmethod
    def decode_token(token: str) -> TokenData:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData object
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(
                user_id=user_id,
                email=payload.get("email"),
                roles=payload.get("roles", []),
                exp=payload.get("exp")
            )
            
        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> TokenData:
        """
        Verify a token and check its type.
        
        Args:
            token: JWT token string
            token_type: Expected token type (access or refresh)
            
        Returns:
            TokenData object
            
        Raises:
            HTTPException: If token is invalid or wrong type
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected: {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return AuthService.decode_token(token)
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    async def refresh_access_token(refresh_token: str) -> Token:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New Token object with fresh access token
        """
        token_data = AuthService.verify_token(refresh_token, token_type="refresh")
        
        # Create new access token with same data
        new_access_token = AuthService.create_access_token({
            "sub": token_data.user_id,
            "email": token_data.email,
            "roles": token_data.roles
        })
        
        return Token(
            access_token=new_access_token,
            refresh_token=refresh_token,  # Keep same refresh token
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )


# Dependency for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Get current user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        TokenData with user information
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    return AuthService.decode_token(token)


# Dependency for optional authentication
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[TokenData]:
    """
    Get current user if authenticated, None otherwise.
    
    Args:
        credentials: Optional HTTP Bearer token credentials
        
    Returns:
        TokenData if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        return AuthService.decode_token(token)
    except HTTPException:
        return None


# Role-based access control
def require_roles(*required_roles: str):
    """
    Dependency to require specific roles for access.
    
    Args:
        required_roles: Roles required for access
        
    Returns:
        Dependency function that checks roles
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        """Check if user has required roles."""
        user_roles = set(current_user.roles)
        required = set(required_roles)
        
        if not required.intersection(user_roles) and "admin" not in user_roles:
            logger.warning(
                f"Access denied for user {current_user.user_id}. "
                f"Required roles: {required_roles}, User roles: {current_user.roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return role_checker


# Rate limiting decorator
class RateLimiter:
    """Rate limiting for API endpoints."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list[datetime]] = {}
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if within limit, False otherwise
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        if user_id in self.requests:
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > window_start
            ]
        else:
            self.requests[user_id] = []
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Dependency to check rate limiting.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        TokenData if within rate limit
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    if not await rate_limiter.check_rate_limit(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    return current_user


# API Key authentication for service accounts
class APIKeyAuth:
    """API Key authentication for service accounts."""
    
    @staticmethod
    def verify_api_key(api_key: str) -> bool:
        """
        Verify an API key.
        
        Args:
            api_key: API key to verify
            
        Returns:
            True if valid, False otherwise
        """
        # In production, check against database
        valid_keys = settings.API_KEYS if hasattr(settings, 'API_KEYS') else []
        return api_key in valid_keys


async def get_api_key(
    api_key: Optional[str] = Depends(
        lambda x_api_key: x_api_key or None
    )
) -> str:
    """
    Dependency to validate API key.
    
    Args:
        api_key: API key from header
        
    Returns:
        Valid API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key or not APIKeyAuth.verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key