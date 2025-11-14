"""
Document repository implementation.
"""
import json
import sqlite3
import aiosqlite
from typing import List, Dict, Any, Optional
from datetime import datetime

from repositories.base import BaseRepository, DocumentMetadata
from core.config import settings
from core.logging import get_logger
from core.exceptions import VectorStoreError

logger = get_logger("document_repository")


class DocumentRepository(BaseRepository[DocumentMetadata]):
    """Repository for document metadata operations."""
    
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
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        source TEXT NOT NULL,
                        chunk_count INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT
                    )
                """)
                await db.commit()
                
            self._initialized = True
            logger.info("Document repository initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize document repository: {e}")
            raise VectorStoreError(f"Database initialization failed: {e}")
    
    async def create(self, entity: DocumentMetadata) -> DocumentMetadata:
        """Create a new document metadata record."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO documents (
                        document_id, filename, file_type, file_size, source,
                        chunk_count, status, error_message, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.document_id,
                    entity.filename,
                    entity.file_type,
                    entity.file_size,
                    entity.source,
                    entity.chunk_count,
                    entity.status,
                    entity.error_message,
                    entity.created_at,
                    entity.updated_at
                ))
                await db.commit()
                
            logger.info(f"Created document metadata: {entity.document_id}")
            return entity
            
        except Exception as e:
            logger.error(f"Failed to create document metadata: {e}")
            raise VectorStoreError(f"Failed to create document: {e}")
    
    async def get_by_id(self, entity_id: str) -> Optional[DocumentMetadata]:
        """Get document metadata by ID."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (entity_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                if row:
                    return DocumentMetadata(
                        document_id=row[0],
                        filename=row[1],
                        file_type=row[2],
                        file_size=row[3],
                        source=row[4],
                        chunk_count=row[5],
                        status=row[6],
                        error_message=row[7],
                        created_at=row[8],
                        updated_at=row[9]
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get document metadata: {e}")
            raise VectorStoreError(f"Failed to get document: {e}")
    
    async def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[DocumentMetadata]:
        """Update document metadata."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Build update query dynamically
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key != 'document_id':  # Don't allow updating primary key
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return await self.get_by_id(entity_id)
            
            # Add updated_at timestamp
            set_clauses.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(entity_id)
            
            query = f"UPDATE documents SET {', '.join(set_clauses)} WHERE document_id = ?"
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, values)
                await db.commit()
                
            logger.info(f"Updated document metadata: {entity_id}")
            return await self.get_by_id(entity_id)
            
        except Exception as e:
            logger.error(f"Failed to update document metadata: {e}")
            raise VectorStoreError(f"Failed to update document: {e}")
    
    async def delete(self, entity_id: str) -> bool:
        """Delete document metadata."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM documents WHERE document_id = ?", (entity_id,)
                )
                await db.commit()
                
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted document metadata: {entity_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete document metadata: {e}")
            raise VectorStoreError(f"Failed to delete document: {e}")
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[DocumentMetadata]:
        """List all documents with pagination."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, skip)
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                documents = []
                for row in rows:
                    documents.append(DocumentMetadata(
                        document_id=row[0],
                        filename=row[1],
                        file_type=row[2],
                        file_size=row[3],
                        source=row[4],
                        chunk_count=row[5],
                        status=row[6],
                        error_message=row[7],
                        created_at=row[8],
                        updated_at=row[9]
                    ))
                
                return documents
                
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise VectorStoreError(f"Failed to list documents: {e}")
    
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[DocumentMetadata]:
        """Find documents by criteria."""
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
            
            query = f"SELECT * FROM documents WHERE {' AND '.join(where_clauses)} ORDER BY created_at DESC"
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, values) as cursor:
                    rows = await cursor.fetchall()
                    
                documents = []
                for row in rows:
                    documents.append(DocumentMetadata(
                        document_id=row[0],
                        filename=row[1],
                        file_type=row[2],
                        file_size=row[3],
                        source=row[4],
                        chunk_count=row[5],
                        status=row[6],
                        error_message=row[7],
                        created_at=row[8],
                        updated_at=row[9]
                    ))
                
                return documents
                
        except Exception as e:
            logger.error(f"Failed to find documents by criteria: {e}")
            raise VectorStoreError(f"Failed to find documents: {e}")
    
    async def get_by_status(self, status: str) -> List[DocumentMetadata]:
        """Get documents by status."""
        return await self.find_by_criteria({"status": status})
    
    async def update_chunk_count(self, document_id: str, chunk_count: int) -> Optional[DocumentMetadata]:
        """Update document chunk count."""
        return await self.update(document_id, {"chunk_count": chunk_count})
    
    async def mark_as_processed(self, document_id: str, chunk_count: int) -> Optional[DocumentMetadata]:
        """Mark document as processed."""
        return await self.update(document_id, {
            "status": "processed",
            "chunk_count": chunk_count,
            "error_message": None
        })
    
    async def mark_as_failed(self, document_id: str, error_message: str) -> Optional[DocumentMetadata]:
        """Mark document as failed."""
        return await self.update(document_id, {
            "status": "failed",
            "error_message": error_message
        })