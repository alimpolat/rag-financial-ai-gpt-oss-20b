"""
Comprehensive unit tests for Document service.
Tests cover document upload, processing, deletion, and metadata management.
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import uuid
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile
import io

from services.document_service import DocumentService
from services.rag_service import RAGService
from repositories.document_repository import DocumentRepository
from repositories.base import DocumentMetadata
from core.exceptions import (
    DocumentProcessingError,
    FileUploadError,
    DocumentNotFoundError
)


class TestDocumentService:
    """Test suite for Document service."""
    
    @pytest.fixture
    async def mock_rag_service(self):
        """Create mock RAG service."""
        mock = MagicMock(spec=RAGService)
        mock.add_documents = AsyncMock(return_value={
            "status": "success",
            "documents_added": 1,
            "processing_time": 0.5
        })
        mock.delete_document = AsyncMock(return_value={
            "status": "success",
            "document_id": "test_id"
        })
        return mock
    
    @pytest.fixture
    async def mock_document_repository(self):
        """Create mock document repository."""
        mock = MagicMock(spec=DocumentRepository)
        mock.create = AsyncMock(return_value="doc_id_123")
        mock.get = AsyncMock(return_value=DocumentMetadata(
            document_id="doc_id_123",
            filename="test.pdf",
            file_type=".pdf",
            file_size=1024,
            upload_timestamp=datetime.utcnow(),
            status="processed",
            page_count=10,
            chunk_count=5
        ))
        mock.update = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)
        mock.list_all = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    async def document_service(self, mock_rag_service, mock_document_repository):
        """Create Document service instance."""
        service = DocumentService(
            rag_service=mock_rag_service,
            document_repository=mock_document_repository
        )
        return service
    
    @pytest.fixture
    def mock_upload_file(self):
        """Create mock uploaded file."""
        file = MagicMock(spec=UploadFile)
        file.filename = "financial_report.pdf"
        file.content_type = "application/pdf"
        file.file = io.BytesIO(b"PDF content here")
        file.read = AsyncMock(return_value=b"PDF content here")
        file.seek = AsyncMock()
        return file
    
    @pytest.fixture
    def mock_document_processor(self):
        """Mock document processor."""
        with patch('services.document_service.DocumentProcessor') as mock:
            processor = MagicMock()
            processor.initialize = AsyncMock()
            processor.process = AsyncMock(return_value={
                "documents": [MagicMock(text="Processed text", metadata={})],
                "page_count": 5,
                "chunk_count": 10,
                "processing_time": 1.2
            })
            mock.return_value = processor
            yield processor
    
    @pytest.mark.asyncio
    async def test_initialization(self, document_service, mock_document_processor):
        """Test document service initialization."""
        await document_service.initialize()
        
        assert document_service.upload_dir.exists()
        mock_document_processor.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_success(
        self, document_service, mock_upload_file, 
        mock_document_processor, mock_rag_service,
        mock_document_repository
    ):
        """Test successful document processing."""
        await document_service.initialize()
        
        with patch('services.document_service.uuid.uuid4', return_value='test-uuid-123'):
            with patch('services.document_service.publish_event', new_callable=AsyncMock):
                result = await document_service.process_document(mock_upload_file)
        
        assert result["status"] == "success"
        assert result["document_id"] == "test-uuid-123"
        assert result["filename"] == "financial_report.pdf"
        assert "processing_time" in result
        
        mock_document_repository.create.assert_called_once()
        mock_document_processor.process.assert_called_once()
        mock_rag_service.add_documents.assert_called_once()
        
        # Verify status update to 'processed'
        update_calls = mock_document_repository.update.call_args_list
        assert any("processed" in str(call) for call in update_calls)
    
    @pytest.mark.asyncio
    async def test_process_document_invalid_file_type(
        self, document_service, mock_document_processor
    ):
        """Test processing document with invalid file type."""
        await document_service.initialize()
        
        invalid_file = MagicMock(spec=UploadFile)
        invalid_file.filename = "script.exe"
        invalid_file.content_type = "application/x-executable"
        
        with pytest.raises(FileUploadError) as exc_info:
            await document_service.process_document(invalid_file)
        
        assert "Invalid file type" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_document_file_too_large(
        self, document_service, mock_document_processor
    ):
        """Test processing document that exceeds size limit."""
        await document_service.initialize()
        
        large_file = MagicMock(spec=UploadFile)
        large_file.filename = "huge_report.pdf"
        large_file.content_type = "application/pdf"
        large_file.read = AsyncMock(return_value=b"x" * (51 * 1024 * 1024))  # 51MB
        large_file.seek = AsyncMock()
        
        with patch('services.document_service.settings.MAX_FILE_SIZE_MB', 50):
            with pytest.raises(FileUploadError) as exc_info:
                await document_service.process_document(large_file)
        
        assert "exceeds maximum size" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_document_processing_failure(
        self, document_service, mock_upload_file,
        mock_document_processor, mock_document_repository
    ):
        """Test handling of document processing failure."""
        await document_service.initialize()
        
        mock_document_processor.process = AsyncMock(
            side_effect=Exception("PDF parsing failed")
        )
        
        with patch('services.document_service.uuid.uuid4', return_value='test-uuid-456'):
            with patch('services.document_service.publish_event', new_callable=AsyncMock):
                with pytest.raises(DocumentProcessingError) as exc_info:
                    await document_service.process_document(mock_upload_file)
        
        assert "Failed to process document" in str(exc_info.value)
        
        # Verify status update to 'failed'
        update_calls = mock_document_repository.update.call_args_list
        assert any("failed" in str(call) for call in update_calls)
    
    @pytest.mark.asyncio
    async def test_get_document_success(
        self, document_service, mock_document_repository
    ):
        """Test successful document retrieval."""
        result = await document_service.get_document("doc_id_123")
        
        assert result["document_id"] == "doc_id_123"
        assert result["filename"] == "test.pdf"
        assert result["status"] == "processed"
        assert result["page_count"] == 10
        mock_document_repository.get.assert_called_once_with("doc_id_123")
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self, document_service, mock_document_repository
    ):
        """Test retrieving non-existent document."""
        mock_document_repository.get = AsyncMock(return_value=None)
        
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await document_service.get_document("non_existent")
        
        assert "Document not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, document_service, mock_document_repository,
        mock_rag_service
    ):
        """Test successful document deletion."""
        with patch('services.document_service.publish_event', new_callable=AsyncMock):
            result = await document_service.delete_document("doc_id_123")
        
        assert result["status"] == "success"
        assert result["document_id"] == "doc_id_123"
        
        mock_document_repository.get.assert_called_once_with("doc_id_123")
        mock_rag_service.delete_document.assert_called_once_with("doc_id_123")
        mock_document_repository.delete.assert_called_once_with("doc_id_123")
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found(
        self, document_service, mock_document_repository
    ):
        """Test deleting non-existent document."""
        mock_document_repository.get = AsyncMock(return_value=None)
        
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await document_service.delete_document("non_existent")
        
        assert "Document not found" in str(exc_info.value)
        mock_document_repository.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_list_documents(
        self, document_service, mock_document_repository
    ):
        """Test listing all documents."""
        mock_documents = [
            DocumentMetadata(
                document_id="doc1",
                filename="report1.pdf",
                file_type=".pdf",
                file_size=1024,
                upload_timestamp=datetime.utcnow(),
                status="processed"
            ),
            DocumentMetadata(
                document_id="doc2",
                filename="report2.docx",
                file_type=".docx",
                file_size=2048,
                upload_timestamp=datetime.utcnow(),
                status="processing"
            )
        ]
        mock_document_repository.list_all = AsyncMock(return_value=mock_documents)
        
        result = await document_service.list_documents()
        
        assert len(result) == 2
        assert result[0]["document_id"] == "doc1"
        assert result[1]["document_id"] == "doc2"
        mock_document_repository.list_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_documents_with_filter(
        self, document_service, mock_document_repository
    ):
        """Test listing documents with status filter."""
        mock_documents = [
            DocumentMetadata(
                document_id="doc1",
                filename="report1.pdf",
                file_type=".pdf",
                file_size=1024,
                upload_timestamp=datetime.utcnow(),
                status="processed"
            )
        ]
        mock_document_repository.list_by_status = AsyncMock(return_value=mock_documents)
        
        result = await document_service.list_documents(status="processed")
        
        assert len(result) == 1
        assert result[0]["status"] == "processed"
        mock_document_repository.list_by_status.assert_called_once_with("processed")
    
    @pytest.mark.asyncio
    async def test_get_statistics(
        self, document_service, mock_document_repository
    ):
        """Test getting document statistics."""
        mock_stats = {
            "total_documents": 50,
            "processed": 45,
            "processing": 3,
            "failed": 2,
            "total_size_mb": 125.5
        }
        mock_document_repository.get_statistics = AsyncMock(return_value=mock_stats)
        
        result = await document_service.get_statistics()
        
        assert result["total_documents"] == 50
        assert result["processed"] == 45
        assert result["processing"] == 3
        assert result["failed"] == 2
        assert result["total_size_mb"] == 125.5
        mock_document_repository.get_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_upload_documents(
        self, document_service, mock_document_processor
    ):
        """Test batch document upload."""
        await document_service.initialize()
        
        files = [
            MagicMock(spec=UploadFile, filename=f"doc{i}.pdf", 
                     content_type="application/pdf",
                     read=AsyncMock(return_value=b"content"),
                     seek=AsyncMock())
            for i in range(3)
        ]
        
        with patch.object(document_service, 'process_document', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = [
                {"status": "success", "document_id": f"doc{i}"}
                for i in range(3)
            ]
            
            results = await document_service.batch_upload(files)
        
        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)
        assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_reprocess_failed_document(
        self, document_service, mock_document_repository,
        mock_document_processor, mock_rag_service
    ):
        """Test reprocessing a failed document."""
        failed_doc = DocumentMetadata(
            document_id="failed_doc",
            filename="failed.pdf",
            file_type=".pdf",
            file_size=1024,
            upload_timestamp=datetime.utcnow(),
            status="failed",
            file_path="/uploads/failed.pdf"
        )
        mock_document_repository.get = AsyncMock(return_value=failed_doc)
        
        with patch('services.document_service.aiofiles.open', create=True) as mock_open:
            mock_file = AsyncMock()
            mock_file.read = AsyncMock(return_value=b"file content")
            mock_open.return_value.__aenter__.return_value = mock_file
            
            with patch('services.document_service.publish_event', new_callable=AsyncMock):
                result = await document_service.reprocess_document("failed_doc")
        
        assert result["status"] == "success"
        assert result["document_id"] == "failed_doc"
        
        # Verify status updates
        update_calls = mock_document_repository.update.call_args_list
        assert any("processing" in str(call) for call in update_calls)
        assert any("processed" in str(call) for call in update_calls)
    
    @pytest.mark.asyncio
    async def test_validate_file_content(
        self, document_service, mock_document_processor
    ):
        """Test file content validation."""
        await document_service.initialize()
        
        # Test valid PDF magic bytes
        valid_pdf = MagicMock(spec=UploadFile)
        valid_pdf.filename = "test.pdf"
        valid_pdf.content_type = "application/pdf"
        valid_pdf.file = io.BytesIO(b"%PDF-1.4 content")
        valid_pdf.read = AsyncMock(return_value=b"%PDF-1.4 content")
        valid_pdf.seek = AsyncMock()
        
        is_valid = await document_service.validate_file_content(valid_pdf)
        assert is_valid is True
        
        # Test invalid content
        invalid_file = MagicMock(spec=UploadFile)
        invalid_file.filename = "test.pdf"
        invalid_file.content_type = "application/pdf"
        invalid_file.file = io.BytesIO(b"Not a PDF")
        invalid_file.read = AsyncMock(return_value=b"Not a PDF")
        invalid_file.seek = AsyncMock()
        
        is_valid = await document_service.validate_file_content(invalid_file)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_uploads(
        self, document_service, mock_document_repository
    ):
        """Test cleanup of old uploaded files."""
        old_docs = [
            DocumentMetadata(
                document_id=f"old_doc_{i}",
                filename=f"old_{i}.pdf",
                file_type=".pdf",
                file_size=1024,
                upload_timestamp=datetime(2023, 1, 1),
                status="processed",
                file_path=f"/uploads/old_{i}.pdf"
            )
            for i in range(5)
        ]
        mock_document_repository.get_old_documents = AsyncMock(return_value=old_docs)
        
        with patch('pathlib.Path.unlink') as mock_unlink:
            result = await document_service.cleanup_old_uploads(days=30)
        
        assert result["files_deleted"] == 5
        assert mock_unlink.call_count == 5
        mock_document_repository.get_old_documents.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_uploads(
        self, document_service, mock_document_processor
    ):
        """Test handling concurrent document uploads."""
        await document_service.initialize()
        
        files = [
            MagicMock(spec=UploadFile, filename=f"concurrent_{i}.pdf",
                     content_type="application/pdf",
                     read=AsyncMock(return_value=b"content"),
                     seek=AsyncMock())
            for i in range(10)
        ]
        
        with patch.object(document_service, 'process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "success", "document_id": "test"}
            
            import asyncio
            results = await asyncio.gather(*[
                document_service.process_document(f) for f in files
            ])
        
        assert len(results) == 10
        assert all(r["status"] == "success" for r in results)
        assert mock_process.call_count == 10