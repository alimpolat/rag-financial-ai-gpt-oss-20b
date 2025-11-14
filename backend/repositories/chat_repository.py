"""
Chat repository implementation for session and message management.
"""
import json
import aiosqlite
from typing import List, Dict, Any, Optional
from datetime import datetime

from repositories.base import BaseRepository, ChatSession, ChatMessage
from core.config import settings
from core.logging import get_logger
from core.exceptions import VectorStoreError

logger = get_logger("chat_repository")


class ChatSessionRepository(BaseRepository[ChatSession]):
    """Repository for chat session operations."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_URL.replace("sqlite:///", "")
        self._initialized = False
    
    async def initialize(self):
        """Initialize the repository and create tables if needed."""
        if self._initialized:
            return
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        message_count INTEGER DEFAULT 0,
                        last_message_at TEXT
                    )
                """)
                await db.commit()
                
            self._initialized = True
            logger.info("Chat session repository initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chat session repository: {e}")
            raise VectorStoreError(f"Database initialization failed: {e}")
    
    async def create(self, entity: ChatSession) -> ChatSession:
        """Create a new chat session."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO chat_sessions (
                        session_id, user_id, created_at, updated_at,
                        message_count, last_message_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entity.session_id,
                    entity.user_id,
                    entity.created_at,
                    entity.updated_at,
                    entity.message_count,
                    entity.last_message_at
                ))
                await db.commit()
                
            logger.info(f"Created chat session: {entity.session_id}")
            return entity
            
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            raise VectorStoreError(f"Failed to create chat session: {e}")
    
    async def get_by_id(self, entity_id: str) -> Optional[ChatSession]:
        """Get chat session by ID."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM chat_sessions WHERE session_id = ?", (entity_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                if row:
                    return ChatSession(
                        session_id=row[0],
                        user_id=row[1],
                        created_at=row[2],
                        updated_at=row[3],
                        message_count=row[4],
                        last_message_at=row[5]
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get chat session: {e}")
            raise VectorStoreError(f"Failed to get chat session: {e}")
    
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[ChatSession]:
        """Update chat session."""
        if not self._initialized:
            await self.initialize()
        
        try:
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key != 'session_id':
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return await self.get_by_id(entity_id)
            
            set_clauses.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(entity_id)
            
            query = f"UPDATE chat_sessions SET {', '.join(set_clauses)} WHERE session_id = ?"
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, values)
                await db.commit()
                
            return await self.get_by_id(entity_id)
            
        except Exception as e:
            logger.error(f"Failed to update chat session: {e}")
            raise VectorStoreError(f"Failed to update chat session: {e}")
    
    async def delete(self, entity_id: str) -> bool:
        """Delete chat session."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM chat_sessions WHERE session_id = ?", (entity_id,)
                )
                await db.commit()
                
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted chat session: {entity_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete chat session: {e}")
            raise VectorStoreError(f"Failed to delete chat session: {e}")
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ChatSession]:
        """List all chat sessions with pagination."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                    (limit, skip)
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                sessions = []
                for row in rows:
                    sessions.append(ChatSession(
                        session_id=row[0],
                        user_id=row[1],
                        created_at=row[2],
                        updated_at=row[3],
                        message_count=row[4],
                        last_message_at=row[5]
                    ))
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to list chat sessions: {e}")
            raise VectorStoreError(f"Failed to list chat sessions: {e}")
    
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[ChatSession]:
        """Find chat sessions by criteria."""
        if not self._initialized:
            await self.initialize()
        
        try:
            where_clauses = []
            values = []
            
            for key, value in criteria.items():
                where_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not where_clauses:
                return await self.list_all()
            
            query = f"SELECT * FROM chat_sessions WHERE {' AND '.join(where_clauses)} ORDER BY updated_at DESC"
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, values) as cursor:
                    rows = await cursor.fetchall()
                    
                sessions = []
                for row in rows:
                    sessions.append(ChatSession(
                        session_id=row[0],
                        user_id=row[1],
                        created_at=row[2],
                        updated_at=row[3],
                        message_count=row[4],
                        last_message_at=row[5]
                    ))
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to find chat sessions: {e}")
            raise VectorStoreError(f"Failed to find chat sessions: {e}")
    
    async def increment_message_count(self, session_id: str) -> Optional[ChatSession]:
        """Increment message count for a session."""
        session = await self.get_by_id(session_id)
        if session:
            return await self.update(session_id, {
                "message_count": session.message_count + 1,
                "last_message_at": datetime.utcnow().isoformat()
            })
        return None


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Repository for chat message operations."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_URL.replace("sqlite:///", "")
        self._initialized = False
    
    async def initialize(self):
        """Initialize the repository and create tables if needed."""
        if self._initialized:
            return
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        message_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        ai_response TEXT NOT NULL,
                        sources TEXT,
                        confidence REAL,
                        processing_time REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
                    )
                """)
                await db.commit()
                
            self._initialized = True
            logger.info("Chat message repository initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chat message repository: {e}")
            raise VectorStoreError(f"Database initialization failed: {e}")
    
    async def create(self, entity: ChatMessage) -> ChatMessage:
        """Create a new chat message."""
        if not self._initialized:
            await self.initialize()
        
        try:
            sources_json = json.dumps(entity.sources) if entity.sources else "[]"
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO chat_messages (
                        message_id, session_id, user_message, ai_response,
                        sources, confidence, processing_time, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.message_id,
                    entity.session_id,
                    entity.user_message,
                    entity.ai_response,
                    sources_json,
                    entity.confidence,
                    entity.processing_time,
                    entity.created_at
                ))
                await db.commit()
                
            logger.info(f"Created chat message: {entity.message_id}")
            return entity
            
        except Exception as e:
            logger.error(f"Failed to create chat message: {e}")
            raise VectorStoreError(f"Failed to create chat message: {e}")
    
    async def get_by_id(self, entity_id: str) -> Optional[ChatMessage]:
        """Get chat message by ID."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM chat_messages WHERE message_id = ?", (entity_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                if row:
                    sources = json.loads(row[4]) if row[4] else []
                    return ChatMessage(
                        message_id=row[0],
                        session_id=row[1],
                        user_message=row[2],
                        ai_response=row[3],
                        sources=sources,
                        confidence=row[5],
                        processing_time=row[6],
                        created_at=row[7]
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get chat message: {e}")
            raise VectorStoreError(f"Failed to get chat message: {e}")
    
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[ChatMessage]:
        """Update chat message (rarely used)."""
        # Messages are typically immutable, but keeping for interface compliance
        return await self.get_by_id(entity_id)
    
    async def delete(self, entity_id: str) -> bool:
        """Delete chat message."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM chat_messages WHERE message_id = ?", (entity_id,)
                )
                await db.commit()
                
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted chat message: {entity_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete chat message: {e}")
            raise VectorStoreError(f"Failed to delete chat message: {e}")
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ChatMessage]:
        """List all chat messages with pagination."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, skip)
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                messages = []
                for row in rows:
                    sources = json.loads(row[4]) if row[4] else []
                    messages.append(ChatMessage(
                        message_id=row[0],
                        session_id=row[1],
                        user_message=row[2],
                        ai_response=row[3],
                        sources=sources,
                        confidence=row[5],
                        processing_time=row[6],
                        created_at=row[7]
                    ))
                
                return messages
                
        except Exception as e:
            logger.error(f"Failed to list chat messages: {e}")
            raise VectorStoreError(f"Failed to list chat messages: {e}")
    
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[ChatMessage]:
        """Find chat messages by criteria."""
        if not self._initialized:
            await self.initialize()
        
        try:
            where_clauses = []
            values = []
            
            for key, value in criteria.items():
                where_clauses.append(f"{key} = ?")
                values.append(value)
            
            if not where_clauses:
                return await self.list_all()
            
            query = f"SELECT * FROM chat_messages WHERE {' AND '.join(where_clauses)} ORDER BY created_at ASC"
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, values) as cursor:
                    rows = await cursor.fetchall()
                    
                messages = []
                for row in rows:
                    sources = json.loads(row[4]) if row[4] else []
                    messages.append(ChatMessage(
                        message_id=row[0],
                        session_id=row[1],
                        user_message=row[2],
                        ai_response=row[3],
                        sources=sources,
                        confidence=row[5],
                        processing_time=row[6],
                        created_at=row[7]
                    ))
                
                return messages
                
        except Exception as e:
            logger.error(f"Failed to find chat messages: {e}")
            raise VectorStoreError(f"Failed to find chat messages: {e}")
    
    async def get_by_session(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get messages for a specific session."""
        return await self.find_by_criteria({"session_id": session_id})