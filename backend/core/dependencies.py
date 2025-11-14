"""
Dependency injection container and service management.
"""
from functools import lru_cache
from typing import AsyncGenerator
import logging

from services.rag_service import RAGService
from services.chat_service import ChatService
from services.document_service import DocumentService
from services.cache_service import CacheService
from repositories.document_repository import DocumentRepository
from repositories.chat_repository import ChatSessionRepository, ChatMessageRepository
from services.event_handlers import (
    DocumentEventHandler, ChatEventHandler, SystemEventHandler,
    MetricsEventHandler, AuditEventHandler
)
from core.events import get_event_bus, shutdown_event_bus
from core.config import settings

logger = logging.getLogger("rag_financial_ai")


class ServiceContainer:
    """Central service container for dependency injection."""
    
    def __init__(self):
        # Services
        self._cache_service: CacheService = None
        self._rag_service: RAGService = None
        self._chat_service: ChatService = None
        self._document_service: DocumentService = None
        
        # Repositories
        self._document_repository: DocumentRepository = None
        self._chat_session_repository: ChatSessionRepository = None
        self._chat_message_repository: ChatMessageRepository = None
        
        # Event handlers
        self._document_event_handler: DocumentEventHandler = None
        self._chat_event_handler: ChatEventHandler = None
        self._system_event_handler: SystemEventHandler = None
        self._metrics_event_handler: MetricsEventHandler = None
        self._audit_event_handler: AuditEventHandler = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all services and repositories."""
        if self._initialized:
            return
            
        logger.info("Initializing service container...")
        
        # Initialize cache service first
        try:
            self._cache_service = CacheService()
            await self._cache_service.initialize()
            logger.info("Cache service initialized successfully")
        except Exception as e:
            logger.warning(f"Cache service initialization failed: {e}. Running without cache.")
            self._cache_service = None
        
        # Initialize repositories
        self._document_repository = DocumentRepository()
        await self._document_repository.initialize()
        
        self._chat_session_repository = ChatSessionRepository()
        await self._chat_session_repository.initialize()
        
        self._chat_message_repository = ChatMessageRepository()
        await self._chat_message_repository.initialize()
        
        # Initialize RAG service with cache
        self._rag_service = RAGService(cache_service=self._cache_service)
        await self._rag_service.initialize()
        
        # Initialize event system
        event_bus = await get_event_bus()
        
        # Initialize event handlers
        self._document_event_handler = DocumentEventHandler(self._document_repository)
        self._chat_event_handler = ChatEventHandler(
            self._chat_session_repository,
            self._chat_message_repository
        )
        self._system_event_handler = SystemEventHandler()
        self._metrics_event_handler = MetricsEventHandler()
        self._audit_event_handler = AuditEventHandler()
        
        # Subscribe event handlers to event bus
        event_bus.subscribe("document.uploaded", self._document_event_handler)
        event_bus.subscribe("document.processing.started", self._document_event_handler)
        event_bus.subscribe("document.processing.completed", self._document_event_handler)
        event_bus.subscribe("document.processing.failed", self._document_event_handler)
        event_bus.subscribe("document.deleted", self._document_event_handler)
        
        event_bus.subscribe("chat.message.received", self._chat_event_handler)
        event_bus.subscribe("chat.message.processed", self._chat_event_handler)
        
        event_bus.subscribe("system.error", self._system_event_handler)
        event_bus.subscribe("system.health.check", self._system_event_handler)
        
        # Metrics handler listens to all events
        for event_type in [
            "document.uploaded", "document.processing.completed", "document.processing.failed",
            "chat.message.received", "chat.message.processed", "system.error"
        ]:
            event_bus.subscribe(event_type, self._metrics_event_handler)
        
        # Audit handler for important events
        for event_type in ["document.uploaded", "document.deleted", "chat.session.created", "system.error"]:
            event_bus.subscribe(event_type, self._audit_event_handler)
        
        # Initialize other services with their dependencies
        self._chat_service = ChatService(rag_service=self._rag_service)
        self._document_service = DocumentService(
            rag_service=self._rag_service,
            document_repository=self._document_repository
        )
        await self._document_service.initialize()
        
        self._initialized = True
        logger.info("Service container initialized successfully")
    
    async def shutdown(self):
        """Cleanup all services."""
        logger.info("Shutting down service container...")
        
        # Shutdown event bus
        await shutdown_event_bus()
        
        # Add cleanup logic if needed
        if self._rag_service:
            await self._rag_service.shutdown()
        
        self._initialized = False
        logger.info("Service container shutdown complete")
    
    @property
    def rag_service(self) -> RAGService:
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        return self._rag_service
    
    @property
    def chat_service(self) -> ChatService:
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        return self._chat_service
    
    @property
    def document_service(self) -> DocumentService:
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        return self._document_service
    
    @property
    def document_repository(self) -> DocumentRepository:
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        return self._document_repository
    
    @property
    def chat_session_repository(self) -> ChatSessionRepository:
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        return self._chat_session_repository
    
    @property
    def chat_message_repository(self) -> ChatMessageRepository:
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        return self._chat_message_repository
    
    @property
    def metrics_event_handler(self) -> MetricsEventHandler:
        if not self._initialized:
            raise RuntimeError("Service container not initialized")
        return self._metrics_event_handler


# Global service container instance
_service_container: ServiceContainer = None


async def get_service_container() -> ServiceContainer:
    """Get or create the global service container."""
    global _service_container
    
    if _service_container is None:
        _service_container = ServiceContainer()
        await _service_container.initialize()
    
    return _service_container


# FastAPI dependency functions
async def get_rag_service() -> RAGService:
    """FastAPI dependency for RAG service."""
    container = await get_service_container()
    return container.rag_service


async def get_chat_service() -> ChatService:
    """FastAPI dependency for chat service."""
    container = await get_service_container()
    return container.chat_service


async def get_document_service() -> DocumentService:
    """FastAPI dependency for document service."""
    container = await get_service_container()
    return container.document_service


async def get_document_repository() -> DocumentRepository:
    """FastAPI dependency for document repository."""
    container = await get_service_container()
    return container.document_repository


async def get_chat_session_repository() -> ChatSessionRepository:
    """FastAPI dependency for chat session repository."""
    container = await get_service_container()
    return container.chat_session_repository


async def get_chat_message_repository() -> ChatMessageRepository:
    """FastAPI dependency for chat message repository."""
    container = await get_service_container()
    return container.chat_message_repository


@lru_cache()
def get_settings():
    """FastAPI dependency for settings."""
    return settings