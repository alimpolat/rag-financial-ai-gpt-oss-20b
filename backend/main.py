"""
FastAPI main application for RAG Financial AI.
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from api.routes import auth, chat, documents, health, metrics
from api.websocket import websocket_endpoint
from core.config import settings
from core.logging import setup_logging, get_logger
from core.dependencies import get_service_container
from core.middleware import (
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    ExceptionHandlingMiddleware,
    SecurityHeadersMiddleware
)
from core.security_middleware import SecurityMiddleware, InputValidationMiddleware

# Setup logging
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting RAG Financial AI application...")
    
    try:
        # Initialize service container
        container = await get_service_container()
        logger.info("Service container initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        logger.info("Shutting down RAG Financial AI application...")
        # Cleanup services
        try:
            container = await get_service_container()
            await container.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="RAG Financial AI API",
    description="A production-ready RAG system for financial document analysis using GPT-OSS:20B",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add custom middleware (order matters - first added is outermost)
app.add_middleware(SecurityMiddleware)
app.add_middleware(InputValidationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ExceptionHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Financial AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy",
        "websocket": "/ws/{client_id}"
    }


# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_route(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication."""
    from services.cache_service import get_cache_service
    cache_service = await get_cache_service()
    await websocket_endpoint(websocket, client_id, cache_service)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
