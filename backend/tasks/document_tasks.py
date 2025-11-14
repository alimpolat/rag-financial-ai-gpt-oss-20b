"""
Celery tasks for async document processing.
Handles document upload, processing, and indexing in the background.
"""
from celery import current_task
from celery_app import app, AsyncTask
import asyncio
import time
from typing import Dict, Any, Optional
from pathlib import Path
import json

from services.document_service import DocumentService
from services.rag_service import RAGService
from services.cache_service import CacheService
from repositories.document_repository import DocumentRepository
from utils.document_processor import DocumentProcessor
from core.logging import get_logger
from core.events import publish_event, DocumentProcessingStartedEvent, DocumentProcessingCompletedEvent, DocumentProcessingFailedEvent

logger = get_logger("document_tasks")


@app.task(bind=True, base=AsyncTask, name='tasks.document_tasks.process_document_async')
class ProcessDocumentTask(AsyncTask):
    """Async document processing task."""
    
    async def async_run(self, document_id: str, file_path: str, 
                       file_name: str, file_type: str) -> Dict[str, Any]:
        """
        Process document asynchronously.
        
        Args:
            document_id: Document identifier
            file_path: Path to uploaded file
            file_name: Original filename
            file_type: File type/extension
            
        Returns:
            Processing result
        """
        try:
            # Update task state
            current_task.update_state(
                state='PROCESSING',
                meta={'status': 'Initializing services...', 'progress': 0}
            )
            
            # Initialize services
            document_repo = DocumentRepository()
            await document_repo.initialize()
            
            cache_service = CacheService()
            await cache_service.initialize()
            
            rag_service = RAGService(cache_service=cache_service)
            await rag_service.initialize()
            
            document_processor = DocumentProcessor()
            await document_processor.initialize()
            
            # Publish processing started event
            await publish_event(DocumentProcessingStartedEvent(
                document_id=document_id,
                filename=file_name
            ))
            
            # Update document status
            await document_repo.update(document_id, {"status": "processing"})
            
            current_task.update_state(
                state='PROCESSING',
                meta={'status': 'Reading document...', 'progress': 20}
            )
            
            # Process document
            start_time = time.time()
            
            # Read file content
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            current_task.update_state(
                state='PROCESSING',
                meta={'status': 'Extracting text and chunking...', 'progress': 40}
            )
            
            # Process document with document processor
            processing_result = await document_processor.process(
                file_content,
                file_name,
                file_type
            )
            
            current_task.update_state(
                state='PROCESSING',
                meta={'status': 'Generating embeddings...', 'progress': 60}
            )
            
            # Add documents to RAG service
            await rag_service.add_documents(processing_result["documents"])
            
            current_task.update_state(
                state='PROCESSING',
                meta={'status': 'Indexing in vector store...', 'progress': 80}
            )
            
            # Update document metadata
            processing_time = time.time() - start_time
            await document_repo.update(document_id, {
                "status": "processed",
                "page_count": processing_result.get("page_count", 0),
                "chunk_count": processing_result.get("chunk_count", 0),
                "processing_time": processing_time
            })
            
            # Publish completion event
            await publish_event(DocumentProcessingCompletedEvent(
                document_id=document_id,
                filename=file_name,
                chunk_count=processing_result.get("chunk_count", 0),
                processing_time=processing_time
            ))
            
            current_task.update_state(
                state='SUCCESS',
                meta={'status': 'Completed', 'progress': 100}
            )
            
            logger.info(f"Document {document_id} processed successfully in {processing_time:.2f}s")
            
            return {
                "status": "success",
                "document_id": document_id,
                "chunk_count": processing_result.get("chunk_count", 0),
                "page_count": processing_result.get("page_count", 0),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            
            # Update document status to failed
            try:
                document_repo = DocumentRepository()
                await document_repo.initialize()
                await document_repo.update(document_id, {
                    "status": "failed",
                    "error_message": str(e)
                })
                
                # Publish failure event
                await publish_event(DocumentProcessingFailedEvent(
                    document_id=document_id,
                    filename=file_name,
                    error=str(e)
                ))
            except Exception as update_error:
                logger.error(f"Failed to update document status: {update_error}")
            
            current_task.update_state(
                state='FAILURE',
                meta={'status': f'Failed: {str(e)}', 'progress': 0}
            )
            
            raise


@app.task(name='tasks.document_tasks.batch_process_documents')
def batch_process_documents(document_batch: list[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process multiple documents in batch.
    
    Args:
        document_batch: List of document metadata
        
    Returns:
        Batch processing results
    """
    results = []
    failed = []
    
    for doc in document_batch:
        try:
            # Queue individual document processing
            task = ProcessDocumentTask()
            result = task.delay(
                doc["document_id"],
                doc["file_path"],
                doc["file_name"],
                doc["file_type"]
            )
            results.append({
                "document_id": doc["document_id"],
                "task_id": result.id,
                "status": "queued"
            })
        except Exception as e:
            failed.append({
                "document_id": doc["document_id"],
                "error": str(e)
            })
    
    return {
        "batch_size": len(document_batch),
        "queued": len(results),
        "failed": len(failed),
        "results": results,
        "failures": failed
    }


@app.task(bind=True, base=AsyncTask, name='tasks.document_tasks.reprocess_document')
class ReprocessDocumentTask(AsyncTask):
    """Reprocess a failed or updated document."""
    
    async def async_run(self, document_id: str) -> Dict[str, Any]:
        """
        Reprocess an existing document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Reprocessing result
        """
        try:
            # Get document metadata
            document_repo = DocumentRepository()
            await document_repo.initialize()
            
            document = await document_repo.get(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Process using main task
            task = ProcessDocumentTask()
            return await task.async_run(
                document_id,
                document.file_path,
                document.filename,
                document.file_type
            )
            
        except Exception as e:
            logger.error(f"Error reprocessing document {document_id}: {e}")
            raise


@app.task(bind=True, base=AsyncTask, name='tasks.document_tasks.cleanup_old_documents')
class CleanupOldDocumentsTask(AsyncTask):
    """Cleanup old processed documents."""
    
    async def async_run(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up documents older than specified days.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Cleanup results
        """
        try:
            from datetime import datetime, timedelta
            
            document_repo = DocumentRepository()
            await document_repo.initialize()
            
            # Get old documents
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_documents = await document_repo.get_old_documents(cutoff_date)
            
            deleted_count = 0
            failed_count = 0
            
            for doc in old_documents:
                try:
                    # Delete file if exists
                    file_path = Path(doc.file_path)
                    if file_path.exists():
                        file_path.unlink()
                    
                    # Delete from database
                    await document_repo.delete(doc.document_id)
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to delete document {doc.document_id}: {e}")
                    failed_count += 1
            
            logger.info(f"Cleanup completed: {deleted_count} deleted, {failed_count} failed")
            
            return {
                "status": "success",
                "deleted": deleted_count,
                "failed": failed_count,
                "total_processed": len(old_documents)
            }
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            raise


@app.task(name='tasks.document_tasks.get_processing_status')
def get_processing_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a document processing task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status and metadata
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=app)
    
    return {
        "task_id": task_id,
        "status": result.state,
        "info": result.info if result.info else {},
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() and result.successful() else None
    }