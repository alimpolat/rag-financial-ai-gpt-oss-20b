"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from core.config import settings
from services.rag_service import RAGService

router = APIRouter()

# Dependency injection for RAGService
def get_rag_service() -> RAGService:
    return RAGService()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME
    }


@router.get("/health/detailed")
async def detailed_health_check(rag_service: RAGService = Depends(get_rag_service)):
    """Detailed health check with service status."""
    # Check Ollama status
    ollama_status = await rag_service.check_ollama_status()
    
    return {
        "status": "healthy" if ollama_status["ollama_running"] else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME,
        "components": {
            "api": "healthy",
            "vector_db": "healthy",
            "ollama": ollama_status["status"],
            "gpt_oss_model": "available" if ollama_status["model_available"] else "not_found"
        },
        "ollama_details": ollama_status
    }
