"""
Base repository interface and abstract classes.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository class."""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Update entity by ID."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        pass
    
    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """List all entities with pagination."""
        pass
    
    @abstractmethod
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """Find entities by criteria."""
        pass


class DocumentMetadata(BaseModel):
    """Document metadata model."""
    document_id: str
    filename: str
    file_type: str
    file_size: int
    source: str
    chunk_count: int
    created_at: str
    updated_at: Optional[str] = None
    status: str = "processed"
    error_message: Optional[str] = None


class ChatSession(BaseModel):
    """Chat session model."""
    session_id: str
    user_id: Optional[str] = None
    created_at: str
    updated_at: str
    message_count: int = 0
    last_message_at: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model."""
    message_id: str
    session_id: str
    user_message: str
    ai_response: str
    sources: List[str]
    confidence: float
    processing_time: float
    created_at: str