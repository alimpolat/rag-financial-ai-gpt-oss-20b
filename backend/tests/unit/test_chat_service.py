"""
Comprehensive unit tests for Chat service.
Tests cover chat sessions, message history, and conversation management.
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid
import json

from services.chat_service import ChatService
from services.rag_service import RAGService
from repositories.chat_repository import ChatSessionRepository, ChatMessageRepository
from repositories.base import ChatSession, ChatMessage
from core.exceptions import (
    ChatSessionError,
    MessageProcessingError,
    SessionNotFoundError
)


class TestChatService:
    """Test suite for Chat service."""
    
    @pytest.fixture
    async def mock_rag_service(self):
        """Create mock RAG service."""
        mock = MagicMock(spec=RAGService)
        mock.query = AsyncMock(return_value={
            "response": "This is a test response from RAG",
            "sources": [
                {
                    "text": "Source document text",
                    "metadata": {"source": "doc1.pdf", "page": 5},
                    "score": 0.92
                }
            ],
            "confidence": 0.85,
            "processing_time": 1.2
        })
        return mock
    
    @pytest.fixture
    async def mock_chat_repository(self):
        """Create mock chat repository."""
        mock = MagicMock(spec=ChatSessionRepository)
        mock.create_session = AsyncMock(return_value="session_123")
        mock.get_session = AsyncMock(return_value=ChatSession(
            session_id="session_123",
            user_id="user_456",
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            message_count=5,
            context_documents=[]
        ))
        mock.add_message = AsyncMock(return_value="msg_789")
        mock.get_messages = AsyncMock(return_value=[])
        mock.update_session = AsyncMock(return_value=True)
        mock.delete_session = AsyncMock(return_value=True)
        mock.list_sessions = AsyncMock(return_value=[])
        return mock
    
    @pytest.fixture
    async def chat_service(self, mock_rag_service, mock_chat_repository):
        """Create Chat service instance."""
        service = ChatService(
            rag_service=mock_rag_service,
            chat_repository=mock_chat_repository
        )
        return service
    
    @pytest.fixture
    def sample_messages(self):
        """Sample chat messages for testing."""
        return [
            ChatMessage(
                message_id="msg1",
                session_id="session_123",
                role="user",
                content="What is the revenue for Q1?",
                timestamp=datetime.utcnow() - timedelta(minutes=5)
            ),
            ChatMessage(
                message_id="msg2",
                session_id="session_123",
                role="assistant",
                content="The revenue for Q1 was $10 million.",
                timestamp=datetime.utcnow() - timedelta(minutes=4),
                sources=[{"source": "report.pdf", "page": 3}],
                confidence=0.9
            )
        ]
    
    @pytest.mark.asyncio
    async def test_create_session_success(
        self, chat_service, mock_chat_repository
    ):
        """Test successful chat session creation."""
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            result = await chat_service.create_session(user_id="user_123")
        
        assert result["session_id"] == "session_123"
        assert result["user_id"] == "user_123"
        assert "created_at" in result
        mock_chat_repository.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_session_with_context(
        self, chat_service, mock_chat_repository
    ):
        """Test creating session with context documents."""
        context_docs = ["doc1.pdf", "doc2.pdf"]
        
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            result = await chat_service.create_session(
                user_id="user_123",
                context_documents=context_docs
            )
        
        assert result["session_id"] == "session_123"
        assert result["context_documents"] == context_docs
        
        # Verify repository was called with correct params
        call_args = mock_chat_repository.create_session.call_args
        assert "context_documents" in call_args.kwargs or \
               context_docs in call_args.args
    
    @pytest.mark.asyncio
    async def test_send_message_success(
        self, chat_service, mock_rag_service,
        mock_chat_repository
    ):
        """Test successful message sending and response."""
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            result = await chat_service.send_message(
                session_id="session_123",
                message="What is the revenue growth?"
            )
        
        assert result["response"] == "This is a test response from RAG"
        assert len(result["sources"]) == 1
        assert result["confidence"] == 0.85
        assert result["session_id"] == "session_123"
        
        # Verify message was saved
        assert mock_chat_repository.add_message.call_count == 2  # User + Assistant
        mock_rag_service.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_with_context(
        self, chat_service, mock_rag_service,
        mock_chat_repository, sample_messages
    ):
        """Test sending message with conversation context."""
        mock_chat_repository.get_messages = AsyncMock(return_value=sample_messages)
        
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            result = await chat_service.send_message(
                session_id="session_123",
                message="Can you provide more details?"
            )
        
        # Verify RAG was called with context
        rag_call_args = mock_rag_service.query.call_args
        query_text = rag_call_args.args[0]
        
        # Should include context in the query
        assert "What is the revenue for Q1?" in query_text or \
               "context" in query_text.lower()
        
        assert result["response"] == "This is a test response from RAG"
    
    @pytest.mark.asyncio
    async def test_send_message_session_not_found(
        self, chat_service, mock_chat_repository
    ):
        """Test sending message to non-existent session."""
        mock_chat_repository.get_session = AsyncMock(return_value=None)
        
        with pytest.raises(SessionNotFoundError) as exc_info:
            await chat_service.send_message(
                session_id="non_existent",
                message="Test message"
            )
        
        assert "Session not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_rag_failure(
        self, chat_service, mock_rag_service,
        mock_chat_repository
    ):
        """Test handling RAG service failure."""
        mock_rag_service.query = AsyncMock(
            side_effect=Exception("RAG service error")
        )
        
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            with pytest.raises(MessageProcessingError) as exc_info:
                await chat_service.send_message(
                    session_id="session_123",
                    message="Test query"
                )
        
        assert "Failed to process message" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_session_history(
        self, chat_service, mock_chat_repository,
        sample_messages
    ):
        """Test retrieving session history."""
        mock_chat_repository.get_messages = AsyncMock(return_value=sample_messages)
        
        result = await chat_service.get_session_history("session_123")
        
        assert result["session_id"] == "session_123"
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][1]["role"] == "assistant"
        assert result["message_count"] == 2
        
        mock_chat_repository.get_messages.assert_called_once_with("session_123")
    
    @pytest.mark.asyncio
    async def test_get_session_history_with_limit(
        self, chat_service, mock_chat_repository,
        sample_messages
    ):
        """Test retrieving limited session history."""
        mock_chat_repository.get_messages = AsyncMock(
            return_value=sample_messages[:1]
        )
        
        result = await chat_service.get_session_history(
            "session_123",
            limit=1
        )
        
        assert len(result["messages"]) == 1
        mock_chat_repository.get_messages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_session(
        self, chat_service, mock_chat_repository
    ):
        """Test deleting a chat session."""
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            result = await chat_service.delete_session("session_123")
        
        assert result["status"] == "success"
        assert result["session_id"] == "session_123"
        
        mock_chat_repository.get_session.assert_called_once_with("session_123")
        mock_chat_repository.delete_session.assert_called_once_with("session_123")
    
    @pytest.mark.asyncio
    async def test_delete_session_not_found(
        self, chat_service, mock_chat_repository
    ):
        """Test deleting non-existent session."""
        mock_chat_repository.get_session = AsyncMock(return_value=None)
        
        with pytest.raises(SessionNotFoundError) as exc_info:
            await chat_service.delete_session("non_existent")
        
        assert "Session not found" in str(exc_info.value)
        mock_chat_repository.delete_session.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_list_user_sessions(
        self, chat_service, mock_chat_repository
    ):
        """Test listing user's chat sessions."""
        sessions = [
            ChatSession(
                session_id="session1",
                user_id="user_123",
                created_at=datetime.utcnow() - timedelta(hours=2),
                last_activity=datetime.utcnow() - timedelta(hours=1),
                message_count=10
            ),
            ChatSession(
                session_id="session2",
                user_id="user_123",
                created_at=datetime.utcnow() - timedelta(days=1),
                last_activity=datetime.utcnow() - timedelta(hours=5),
                message_count=5
            )
        ]
        mock_chat_repository.list_sessions = AsyncMock(return_value=sessions)
        
        result = await chat_service.list_user_sessions("user_123")
        
        assert len(result) == 2
        assert result[0]["session_id"] == "session1"
        assert result[0]["message_count"] == 10
        assert result[1]["session_id"] == "session2"
        
        mock_chat_repository.list_sessions.assert_called_once_with(
            user_id="user_123"
        )
    
    @pytest.mark.asyncio
    async def test_summarize_session(
        self, chat_service, mock_chat_repository,
        mock_rag_service, sample_messages
    ):
        """Test generating session summary."""
        mock_chat_repository.get_messages = AsyncMock(return_value=sample_messages)
        mock_rag_service.query = AsyncMock(return_value={
            "response": "Summary: Discussion about Q1 revenue of $10 million.",
            "sources": [],
            "confidence": 0.95,
            "processing_time": 0.8
        })
        
        result = await chat_service.summarize_session("session_123")
        
        assert "summary" in result
        assert "Q1 revenue" in result["summary"]
        assert result["message_count"] == 2
        
        # Verify RAG was called with summarization prompt
        rag_call_args = mock_rag_service.query.call_args
        query_text = rag_call_args.args[0]
        assert "summarize" in query_text.lower()
    
    @pytest.mark.asyncio
    async def test_export_session(
        self, chat_service, mock_chat_repository,
        sample_messages
    ):
        """Test exporting session to different formats."""
        mock_chat_repository.get_messages = AsyncMock(return_value=sample_messages)
        
        # Test JSON export
        json_result = await chat_service.export_session(
            "session_123",
            format="json"
        )
        assert "session_id" in json_result
        assert "messages" in json_result
        assert len(json_result["messages"]) == 2
        
        # Test markdown export
        md_result = await chat_service.export_session(
            "session_123",
            format="markdown"
        )
        assert isinstance(md_result, str)
        assert "# Chat Session" in md_result
        assert "**User:**" in md_result
        assert "**Assistant:**" in md_result
    
    @pytest.mark.asyncio
    async def test_clear_session_context(
        self, chat_service, mock_chat_repository
    ):
        """Test clearing session context documents."""
        result = await chat_service.clear_session_context("session_123")
        
        assert result["status"] == "success"
        assert result["session_id"] == "session_123"
        
        # Verify session was updated with empty context
        update_calls = mock_chat_repository.update_session.call_args_list
        assert any("context_documents" in str(call) for call in update_calls)
    
    @pytest.mark.asyncio
    async def test_get_session_statistics(
        self, chat_service, mock_chat_repository
    ):
        """Test getting session statistics."""
        stats = {
            "total_sessions": 100,
            "active_sessions": 25,
            "total_messages": 5000,
            "avg_messages_per_session": 50,
            "total_users": 30
        }
        mock_chat_repository.get_statistics = AsyncMock(return_value=stats)
        
        result = await chat_service.get_statistics()
        
        assert result["total_sessions"] == 100
        assert result["active_sessions"] == 25
        assert result["total_messages"] == 5000
        assert result["avg_messages_per_session"] == 50
        
        mock_chat_repository.get_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(
        self, chat_service, mock_chat_repository
    ):
        """Test cleaning up old inactive sessions."""
        old_sessions = [
            ChatSession(
                session_id=f"old_{i}",
                user_id="user_123",
                created_at=datetime.utcnow() - timedelta(days=35),
                last_activity=datetime.utcnow() - timedelta(days=31),
                message_count=2
            )
            for i in range(5)
        ]
        mock_chat_repository.get_inactive_sessions = AsyncMock(
            return_value=old_sessions
        )
        mock_chat_repository.delete_session = AsyncMock(return_value=True)
        
        result = await chat_service.cleanup_old_sessions(days=30)
        
        assert result["sessions_deleted"] == 5
        assert mock_chat_repository.delete_session.call_count == 5
    
    @pytest.mark.asyncio
    async def test_regenerate_response(
        self, chat_service, mock_rag_service,
        mock_chat_repository, sample_messages
    ):
        """Test regenerating the last assistant response."""
        mock_chat_repository.get_messages = AsyncMock(return_value=sample_messages)
        mock_chat_repository.delete_message = AsyncMock(return_value=True)
        
        # New response from RAG
        mock_rag_service.query = AsyncMock(return_value={
            "response": "Regenerated: The Q1 revenue was $10.2 million.",
            "sources": [{"source": "updated_report.pdf", "page": 4}],
            "confidence": 0.92,
            "processing_time": 1.1
        })
        
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            result = await chat_service.regenerate_response("session_123")
        
        assert "Regenerated" in result["response"]
        assert result["confidence"] == 0.92
        
        # Verify old message was deleted and new one added
        mock_chat_repository.delete_message.assert_called_once()
        assert mock_chat_repository.add_message.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_concurrent_messages(
        self, chat_service, mock_rag_service,
        mock_chat_repository
    ):
        """Test handling concurrent messages in the same session."""
        import asyncio
        
        messages = [f"Question {i}" for i in range(5)]
        
        with patch('services.chat_service.publish_event', new_callable=AsyncMock):
            # Send multiple messages concurrently
            results = await asyncio.gather(*[
                chat_service.send_message("session_123", msg)
                for msg in messages
            ])
        
        assert len(results) == 5
        assert all("response" in r for r in results)
        assert mock_rag_service.query.call_count == 5
        assert mock_chat_repository.add_message.call_count == 10  # 5 user + 5 assistant
    
    @pytest.mark.asyncio
    async def test_message_feedback(
        self, chat_service, mock_chat_repository
    ):
        """Test adding feedback to messages."""
        result = await chat_service.add_message_feedback(
            message_id="msg_123",
            feedback="helpful",
            rating=5
        )
        
        assert result["status"] == "success"
        assert result["message_id"] == "msg_123"
        
        # Verify message was updated with feedback
        update_calls = mock_chat_repository.update_message.call_args_list
        assert any("feedback" in str(call) for call in update_calls)