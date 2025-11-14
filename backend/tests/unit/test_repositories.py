"""
Unit tests for repository implementations.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from repositories.base import DocumentMetadata, ChatSession, ChatMessage
from repositories.document_repository import DocumentRepository
from repositories.chat_repository import ChatSessionRepository, ChatMessageRepository
from core.exceptions import VectorStoreError


@pytest.mark.unit
@pytest.mark.asyncio
class TestDocumentRepository:
    """Test document repository functionality."""
    
    async def test_create_document(self, document_repository: DocumentRepository):
        """Test creating a document metadata record."""
        document = DocumentMetadata(
            document_id="doc-123",
            filename="test.pdf",
            file_type=".pdf",
            file_size=1024,
            source="test.pdf",
            chunk_count=0,
            status="processing",
            created_at=datetime.utcnow().isoformat()
        )
        
        result = await document_repository.create(document)
        
        assert result.document_id == "doc-123"
        assert result.filename == "test.pdf"
        assert result.status == "processing"
    
    async def test_get_document_by_id(self, document_repository: DocumentRepository):
        """Test retrieving a document by ID."""
        # Create a document first
        document = DocumentMetadata(
            document_id="doc-456",
            filename="test2.pdf",
            file_type=".pdf",
            file_size=2048,
            source="test2.pdf",
            chunk_count=5,
            status="processed",
            created_at=datetime.utcnow().isoformat()
        )
        await document_repository.create(document)
        
        # Retrieve it
        result = await document_repository.get_by_id("doc-456")
        
        assert result is not None
        assert result.document_id == "doc-456"
        assert result.filename == "test2.pdf"
        assert result.chunk_count == 5
        assert result.status == "processed"
    
    async def test_get_nonexistent_document(self, document_repository: DocumentRepository):
        """Test retrieving a non-existent document."""
        result = await document_repository.get_by_id("nonexistent")
        assert result is None
    
    async def test_update_document(self, document_repository: DocumentRepository):
        """Test updating a document."""
        # Create a document first
        document = DocumentMetadata(
            document_id="doc-789",
            filename="test3.pdf",
            file_type=".pdf",
            file_size=1024,
            source="test3.pdf",
            chunk_count=0,
            status="processing",
            created_at=datetime.utcnow().isoformat()
        )
        await document_repository.create(document)
        
        # Update it
        updates = {"status": "processed", "chunk_count": 10}
        result = await document_repository.update("doc-789", updates)
        
        assert result is not None
        assert result.status == "processed"
        assert result.chunk_count == 10
        assert result.updated_at is not None
    
    async def test_delete_document(self, document_repository: DocumentRepository):
        """Test deleting a document."""
        # Create a document first
        document = DocumentMetadata(
            document_id="doc-delete",
            filename="delete.pdf",
            file_type=".pdf",
            file_size=1024,
            source="delete.pdf",
            chunk_count=0,
            status="processing",
            created_at=datetime.utcnow().isoformat()
        )
        await document_repository.create(document)
        
        # Delete it
        result = await document_repository.delete("doc-delete")
        assert result is True
        
        # Verify it's gone
        deleted_doc = await document_repository.get_by_id("doc-delete")
        assert deleted_doc is None
    
    async def test_list_documents(self, document_repository: DocumentRepository):
        """Test listing documents with pagination."""
        # Create multiple documents
        for i in range(5):
            document = DocumentMetadata(
                document_id=f"doc-list-{i}",
                filename=f"test{i}.pdf",
                file_type=".pdf",
                file_size=1024,
                source=f"test{i}.pdf",
                chunk_count=i,
                status="processed",
                created_at=datetime.utcnow().isoformat()
            )
            await document_repository.create(document)
        
        # List all documents
        documents = await document_repository.list_all()
        assert len(documents) >= 5
        
        # Test pagination
        page1 = await document_repository.list_all(skip=0, limit=2)
        assert len(page1) == 2
        
        page2 = await document_repository.list_all(skip=2, limit=2)
        assert len(page2) == 2
        
        # Ensure different documents
        page1_ids = {doc.document_id for doc in page1}
        page2_ids = {doc.document_id for doc in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    async def test_find_by_criteria(self, document_repository: DocumentRepository):
        """Test finding documents by criteria."""
        # Create documents with different statuses
        for status in ["processing", "processed", "failed"]:
            document = DocumentMetadata(
                document_id=f"doc-{status}",
                filename=f"{status}.pdf",
                file_type=".pdf",
                file_size=1024,
                source=f"{status}.pdf",
                chunk_count=0,
                status=status,
                created_at=datetime.utcnow().isoformat()
            )
            await document_repository.create(document)
        
        # Find processed documents
        processed_docs = await document_repository.find_by_criteria({"status": "processed"})
        assert all(doc.status == "processed" for doc in processed_docs)
        assert len(processed_docs) >= 1
    
    async def test_mark_as_processed(self, document_repository: DocumentRepository):
        """Test marking document as processed."""
        # Create a processing document
        document = DocumentMetadata(
            document_id="doc-mark-processed",
            filename="mark.pdf",
            file_type=".pdf",
            file_size=1024,
            source="mark.pdf",
            chunk_count=0,
            status="processing",
            created_at=datetime.utcnow().isoformat()
        )
        await document_repository.create(document)
        
        # Mark as processed
        result = await document_repository.mark_as_processed("doc-mark-processed", 15)
        
        assert result is not None
        assert result.status == "processed"
        assert result.chunk_count == 15
        assert result.error_message is None
    
    async def test_mark_as_failed(self, document_repository: DocumentRepository):
        """Test marking document as failed."""
        # Create a processing document
        document = DocumentMetadata(
            document_id="doc-mark-failed",
            filename="fail.pdf",
            file_type=".pdf",
            file_size=1024,
            source="fail.pdf",
            chunk_count=0,
            status="processing",
            created_at=datetime.utcnow().isoformat()
        )
        await document_repository.create(document)
        
        # Mark as failed
        error_msg = "Processing failed due to invalid format"
        result = await document_repository.mark_as_failed("doc-mark-failed", error_msg)
        
        assert result is not None
        assert result.status == "failed"
        assert result.error_message == error_msg


@pytest.mark.unit
@pytest.mark.asyncio
class TestChatSessionRepository:
    """Test chat session repository functionality."""
    
    async def test_create_chat_session(self, chat_session_repository: ChatSessionRepository):
        """Test creating a chat session."""
        now = datetime.utcnow().isoformat()
        session = ChatSession(
            session_id="session-123",
            user_id="user-456",
            created_at=now,
            updated_at=now,
            message_count=0
        )
        
        result = await chat_session_repository.create(session)
        
        assert result.session_id == "session-123"
        assert result.user_id == "user-456"
        assert result.message_count == 0
    
    async def test_get_chat_session(self, chat_session_repository: ChatSessionRepository):
        """Test retrieving a chat session."""
        # Create session first
        now = datetime.utcnow().isoformat()
        session = ChatSession(
            session_id="session-get",
            user_id="user-get",
            created_at=now,
            updated_at=now,
            message_count=5
        )
        await chat_session_repository.create(session)
        
        # Retrieve it
        result = await chat_session_repository.get_by_id("session-get")
        
        assert result is not None
        assert result.session_id == "session-get"
        assert result.user_id == "user-get"
        assert result.message_count == 5
    
    async def test_increment_message_count(self, chat_session_repository: ChatSessionRepository):
        """Test incrementing message count."""
        # Create session
        now = datetime.utcnow().isoformat()
        session = ChatSession(
            session_id="session-increment",
            user_id="user-increment",
            created_at=now,
            updated_at=now,
            message_count=0
        )
        await chat_session_repository.create(session)
        
        # Increment count
        result = await chat_session_repository.increment_message_count("session-increment")
        
        assert result is not None
        assert result.message_count == 1
        assert result.last_message_at is not None
    
    async def test_find_sessions_by_user(self, chat_session_repository: ChatSessionRepository):
        """Test finding sessions by user ID."""
        now = datetime.utcnow().isoformat()
        
        # Create sessions for different users
        for user_id in ["user-a", "user-b", "user-a"]:
            session = ChatSession(
                session_id=f"session-{user_id}-{len(user_id)}",
                user_id=user_id,
                created_at=now,
                updated_at=now,
                message_count=0
            )
            await chat_session_repository.create(session)
        
        # Find sessions for user-a
        user_a_sessions = await chat_session_repository.find_by_criteria({"user_id": "user-a"})
        assert len(user_a_sessions) == 2
        assert all(session.user_id == "user-a" for session in user_a_sessions)


@pytest.mark.unit
@pytest.mark.asyncio
class TestChatMessageRepository:
    """Test chat message repository functionality."""
    
    async def test_create_chat_message(self, chat_message_repository: ChatMessageRepository):
        """Test creating a chat message."""
        message = ChatMessage(
            message_id="msg-123",
            session_id="session-123",
            user_message="What is the revenue?",
            ai_response="The revenue is $1M.",
            sources=["doc1.pdf", "doc2.pdf"],
            confidence=0.85,
            processing_time=1.5,
            created_at=datetime.utcnow().isoformat()
        )
        
        result = await chat_message_repository.create(message)
        
        assert result.message_id == "msg-123"
        assert result.session_id == "session-123"
        assert result.user_message == "What is the revenue?"
        assert result.ai_response == "The revenue is $1M."
        assert result.sources == ["doc1.pdf", "doc2.pdf"]
        assert result.confidence == 0.85
        assert result.processing_time == 1.5
    
    async def test_get_chat_message(self, chat_message_repository: ChatMessageRepository):
        """Test retrieving a chat message."""
        # Create message first
        message = ChatMessage(
            message_id="msg-get",
            session_id="session-get",
            user_message="Test question",
            ai_response="Test response",
            sources=["test.pdf"],
            confidence=0.9,
            processing_time=0.8,
            created_at=datetime.utcnow().isoformat()
        )
        await chat_message_repository.create(message)
        
        # Retrieve it
        result = await chat_message_repository.get_by_id("msg-get")
        
        assert result is not None
        assert result.message_id == "msg-get"
        assert result.session_id == "session-get"
        assert result.user_message == "Test question"
        assert result.sources == ["test.pdf"]
    
    async def test_get_messages_by_session(self, chat_message_repository: ChatMessageRepository):
        """Test retrieving messages for a session."""
        session_id = "session-messages"
        
        # Create multiple messages for the session
        for i in range(3):
            message = ChatMessage(
                message_id=f"msg-{i}",
                session_id=session_id,
                user_message=f"Question {i}",
                ai_response=f"Response {i}",
                sources=[f"doc{i}.pdf"],
                confidence=0.8 + i * 0.05,
                processing_time=1.0 + i * 0.1,
                created_at=datetime.utcnow().isoformat()
            )
            await chat_message_repository.create(message)
        
        # Get messages for session
        messages = await chat_message_repository.get_by_session(session_id)
        
        assert len(messages) == 3
        assert all(msg.session_id == session_id for msg in messages)
        
        # Should be ordered by creation time (oldest first)
        message_ids = [msg.message_id for msg in messages]
        assert "msg-0" in message_ids
        assert "msg-1" in message_ids
        assert "msg-2" in message_ids
    
    async def test_find_messages_by_criteria(self, chat_message_repository: ChatMessageRepository):
        """Test finding messages by criteria."""
        # Create messages with different confidence levels
        for i, confidence in enumerate([0.7, 0.85, 0.95]):
            message = ChatMessage(
                message_id=f"msg-confidence-{i}",
                session_id="session-confidence",
                user_message=f"Question {i}",
                ai_response=f"Response {i}",
                sources=[f"doc{i}.pdf"],
                confidence=confidence,
                processing_time=1.0,
                created_at=datetime.utcnow().isoformat()
            )
            await chat_message_repository.create(message)
        
        # Find messages for the session
        session_messages = await chat_message_repository.find_by_criteria({
            "session_id": "session-confidence"
        })
        
        assert len(session_messages) == 3
        assert all(msg.session_id == "session-confidence" for msg in session_messages)


@pytest.mark.unit
class TestRepositoryErrorHandling:
    """Test repository error handling."""
    
    @patch('aiosqlite.connect')
    async def test_database_connection_error(self, mock_connect):
        """Test handling of database connection errors."""
        mock_connect.side_effect = Exception("Database connection failed")
        
        repo = DocumentRepository(db_path="invalid.db")
        
        with pytest.raises(VectorStoreError) as exc_info:
            await repo.initialize()
        
        assert "Database initialization failed" in str(exc_info.value)
    
    async def test_invalid_update_parameters(self, document_repository: DocumentRepository):
        """Test update with invalid parameters."""
        # Try to update non-existent document
        result = await document_repository.update("nonexistent", {"status": "processed"})
        
        # Should return None for non-existent document
        assert result is None
    
    async def test_empty_criteria_search(self, document_repository: DocumentRepository):
        """Test search with empty criteria."""
        # Should return all documents (same as list_all)
        result = await document_repository.find_by_criteria({})
        all_docs = await document_repository.list_all()
        
        assert len(result) == len(all_docs)