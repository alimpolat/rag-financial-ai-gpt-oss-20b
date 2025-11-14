"""
Document processing and management service.
"""
import os
import uuid
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
from fastapi import UploadFile

from core.config import settings
from core.logging import get_logger
from core.exceptions import DocumentProcessingError, FileUploadError
from core.events import (
    publish_event, DocumentUploadedEvent, DocumentProcessingStartedEvent,
    DocumentProcessingCompletedEvent, DocumentProcessingFailedEvent,
    DocumentDeletedEvent
)
from services.rag_service import RAGService
from repositories.document_repository import DocumentRepository
from repositories.base import DocumentMetadata
from utils.document_processor import DocumentProcessor
from datetime import datetime

logger = get_logger("document_service")


class DocumentService:
    """Service for handling document operations."""
    
    def __init__(self, rag_service: RAGService, document_repository: DocumentRepository):
        self.rag_service = rag_service
        self.document_repository = document_repository
        self.document_processor = DocumentProcessor()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize the document service."""
        logger.info("Initializing document service...")
        # RAG service is already initialized via dependency injection
        await self.document_processor.initialize()
        logger.info("Document service initialized successfully")
    
    async def process_document(self, file: UploadFile) -> Dict[str, Any]:
        """
        Process an uploaded document.
        
        Args:
            file: Uploaded file
            
        Returns:
            Dictionary containing processing results
        """
        processing_start_time = time.time()
        document_id = str(uuid.uuid4())
        
        try:
            # Create document metadata record
            file_size = 0
            try:
                # Read file to get size
                content = await file.read()
                file_size = len(content)
                await file.seek(0)  # Reset file pointer
            except Exception as e:
                logger.warning(f"Could not determine file size: {e}")
            
            # Publish document uploaded event
            await publish_event(DocumentUploadedEvent(
                document_id=document_id,
                filename=file.filename,
                file_size=file_size,
                file_type=Path(file.filename).suffix.lower()
            ))
            
            document_metadata = DocumentMetadata(
                document_id=document_id,
                filename=file.filename,
                file_type=Path(file.filename).suffix.lower(),
                file_size=file_size,
                source=str(file.filename),
                chunk_count=0,
                status="processing",
                created_at=datetime.utcnow().isoformat()
            )
            
            # Save metadata to repository
            await self.document_repository.create(document_metadata)
            
            # Publish processing started event
            await publish_event(DocumentProcessingStartedEvent(
                document_id=document_id,
                filename=file.filename
            ))
            
            # Save uploaded file
            file_path = await self._save_uploaded_file(file, document_id)
            
            # Process document content
            chunks = await self.document_processor.process_file(
                file_path=file_path,
                document_id=document_id,
                filename=file.filename
            )
            
            # Store chunks in vector database via RAG service
            await self.rag_service.add_documents(chunks)
            
            # Update document metadata as processed
            await self.document_repository.mark_as_processed(document_id, len(chunks))
            
            processing_time = time.time() - processing_start_time
            
            # Publish processing completed event
            await publish_event(DocumentProcessingCompletedEvent(
                document_id=document_id,
                filename=file.filename,
                chunk_count=len(chunks),
                processing_time=processing_time
            ))
            
            logger.info(f"Successfully processed document {file.filename}: {len(chunks)} chunks created")
            
            return {
                "document_id": document_id,
                "filename": file.filename,
                "chunks_created": len(chunks),
                "file_path": str(file_path),
                "status": "processed",
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = time.time() - processing_start_time
            
            logger.error(f"Error processing document: {e}")
            
            # Publish processing failed event
            await publish_event(DocumentProcessingFailedEvent(
                document_id=document_id,
                filename=file.filename,
                error_message=str(e),
                error_type=type(e).__name__,
                processing_time=processing_time
            ))
            
            # Mark document as failed if metadata exists
            try:
                await self.document_repository.mark_as_failed(document_id, str(e))
            except:
                pass  # Ignore repository errors during error handling
                
            raise DocumentProcessingError(f"Failed to process document: {e}")
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all processed documents."""
        try:
            # Get documents from repository
            documents = await self.document_repository.list_all()
            
            # Convert to dict format for API response
            result = []
            for doc in documents:
                result.append({
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "source": doc.source,
                    "chunk_count": doc.chunk_count,
                    "status": doc.status,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                    "error_message": doc.error_message
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise DocumentProcessingError(f"Failed to list documents: {e}")
    
    async def delete_document(self, document_id: str):
        """
        Delete a document and its embeddings.
        
        Args:
            document_id: ID of document to delete
        """
        try:
            # Get document metadata before deletion
            doc_metadata = await self.document_repository.get_by_id(document_id)
            filename = doc_metadata.filename if doc_metadata else "unknown"
            
            # Delete from vector store via RAG service
            await self.rag_service.delete_documents(document_id)
            
            # Delete from repository
            await self.document_repository.delete(document_id)
            
            # Delete physical file if exists
            await self._delete_physical_file(document_id)
            
            # Publish document deleted event
            await publish_event(DocumentDeletedEvent(
                document_id=document_id,
                filename=filename
            ))
            
            logger.info(f"Successfully deleted document {document_id}")
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise DocumentProcessingError(f"Failed to delete document: {e}")
    
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get chunks for a specific document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of document chunks
        """
        try:
            # Get chunks from ChromaDB directly
            if self.rag_service.chroma_client:
                collection = self.rag_service.chroma_client.get_collection("financial_documents")
                
                # Query for specific document
                results = collection.get(
                    where={"document_id": document_id},
                    include=["documents", "metadatas", "ids"]
                )
                
                chunks = []
                if results["documents"]:
                    for i in range(len(results["documents"])):
                        chunks.append({
                            "id": results["ids"][i],
                            "content": results["documents"][i],
                            "metadata": results["metadatas"][i]
                        })
                
                # Sort by chunk_index if available
                chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
                
                return chunks
            else:
                return []
        except Exception as e:
            logger.error(f"Error retrieving document chunks: {e}")
            raise
    
    async def _save_uploaded_file(self, file: UploadFile, document_id: str) -> Path:
        """Save uploaded file to disk."""
        file_extension = Path(file.filename).suffix
        file_path = self.upload_dir / f"{document_id}{file_extension}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        return file_path
    
    async def _delete_physical_file(self, document_id: str):
        """Delete physical file from disk."""
        # Find file with document_id prefix
        for file_path in self.upload_dir.glob(f"{document_id}.*"):
            try:
                os.remove(file_path)
                logger.info(f"Deleted physical file: {file_path}")
            except OSError as e:
                logger.warning(f"Could not delete file {file_path}: {e}")
