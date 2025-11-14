"""
Unit tests for the event system.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from core.events import (
    EventBus, BaseEvent, EventHandler, EventPriority,
    DocumentUploadedEvent, DocumentProcessingCompletedEvent,
    ChatMessageReceivedEvent, SystemErrorEvent,
    publish_event, get_event_bus, shutdown_event_bus
)


class TestEvent(BaseEvent):
    """Test event for unit testing."""
    
    def __init__(self, data: str):
        super().__init__()
        self.data = data
    
    @property
    def event_type(self) -> str:
        return "test.event"


class TestEventHandler(EventHandler):
    """Test event handler."""
    
    def __init__(self):
        self.handled_events = []
        self.handle_count = 0
    
    async def handle(self, event: BaseEvent) -> None:
        self.handled_events.append(event)
        self.handle_count += 1
    
    def can_handle(self, event_type: str) -> bool:
        return event_type.startswith("test.")


@pytest.mark.unit
class TestBaseEvent:
    """Test base event functionality."""
    
    def test_event_creation(self):
        """Test event creation with default values."""
        event = TestEvent("test data")
        
        assert event.data == "test data"
        assert event.event_type == "test.event"
        assert event.priority == EventPriority.NORMAL
        assert event.correlation_id is None
        assert isinstance(event.timestamp, datetime)
        assert event.event_id is not None
    
    def test_event_to_dict(self):
        """Test event serialization to dictionary."""
        event = TestEvent("test data")
        event.correlation_id = "test-correlation-id"
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "test.event"
        assert event_dict["correlation_id"] == "test-correlation-id"
        assert event_dict["priority"] == EventPriority.NORMAL.value
        assert "data" in event_dict
        assert event_dict["data"]["data"] == "test data"


@pytest.mark.unit
class TestDocumentEvents:
    """Test document-related events."""
    
    def test_document_uploaded_event(self):
        """Test document uploaded event creation."""
        event = DocumentUploadedEvent(
            document_id="doc-123",
            filename="test.pdf",
            file_size=1024,
            file_type=".pdf",
            user_id="user-456"
        )
        
        assert event.event_type == "document.uploaded"
        assert event.document_id == "doc-123"
        assert event.filename == "test.pdf"
        assert event.file_size == 1024
        assert event.file_type == ".pdf"
        assert event.user_id == "user-456"
    
    def test_document_processing_completed_event(self):
        """Test document processing completed event."""
        event = DocumentProcessingCompletedEvent(
            document_id="doc-123",
            filename="test.pdf",
            chunk_count=5,
            processing_time=2.5
        )
        
        assert event.event_type == "document.processing.completed"
        assert event.document_id == "doc-123"
        assert event.chunk_count == 5
        assert event.processing_time == 2.5


@pytest.mark.unit
class TestChatEvents:
    """Test chat-related events."""
    
    def test_chat_message_received_event(self):
        """Test chat message received event."""
        event = ChatMessageReceivedEvent(
            session_id="session-123",
            message_id="msg-456",
            user_message="What is the revenue?",
            user_id="user-789"
        )
        
        assert event.event_type == "chat.message.received"
        assert event.session_id == "session-123"
        assert event.message_id == "msg-456"
        assert event.user_message == "What is the revenue?"
        assert event.user_id == "user-789"


@pytest.mark.unit
class TestSystemEvents:
    """Test system-related events."""
    
    def test_system_error_event(self):
        """Test system error event."""
        event = SystemErrorEvent(
            error_message="Test error",
            error_type="TestError",
            service_name="test_service"
        )
        
        assert event.event_type == "system.error"
        assert event.error_message == "Test error"
        assert event.error_type == "TestError"
        assert event.service_name == "test_service"
        assert event.priority == EventPriority.HIGH


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventBus:
    """Test event bus functionality."""
    
    async def test_event_bus_creation(self):
        """Test event bus creation and basic properties."""
        bus = EventBus()
        
        assert not bus._running
        assert bus._event_queue.qsize() == 0
        assert len(bus._worker_tasks) == 0
        assert bus._processed_events == 0
        assert bus._failed_events == 0
    
    async def test_event_bus_start_stop(self):
        """Test starting and stopping the event bus."""
        bus = EventBus()
        
        # Start bus
        await bus.start()
        assert bus._running
        assert len(bus._worker_tasks) == bus._max_workers
        
        # Stop bus
        await bus.stop()
        assert not bus._running
        assert len(bus._worker_tasks) == 0
    
    async def test_handler_subscription(self):
        """Test subscribing and unsubscribing event handlers."""
        bus = EventBus()
        handler = TestEventHandler()
        
        # Subscribe handler
        bus.subscribe("test.event", handler)
        assert "test.event" in bus._handlers
        assert handler in bus._handlers["test.event"]
        
        # Unsubscribe handler
        bus.unsubscribe("test.event", handler)
        assert handler not in bus._handlers.get("test.event", [])
    
    async def test_event_publishing_and_handling(self):
        """Test publishing events and handler execution."""
        bus = EventBus()
        handler = TestEventHandler()
        
        # Subscribe handler and start bus
        bus.subscribe("test.event", handler)
        await bus.start()
        
        try:
            # Publish event
            event = TestEvent("test data")
            await bus.publish(event)
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Check handler was called
            assert handler.handle_count == 1
            assert len(handler.handled_events) == 1
            assert handler.handled_events[0].data == "test data"
            
        finally:
            await bus.stop()
    
    async def test_multiple_handlers(self):
        """Test multiple handlers for the same event."""
        bus = EventBus()
        handler1 = TestEventHandler()
        handler2 = TestEventHandler()
        
        # Subscribe multiple handlers
        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)
        await bus.start()
        
        try:
            # Publish event
            event = TestEvent("test data")
            await bus.publish(event)
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Check both handlers were called
            assert handler1.handle_count == 1
            assert handler2.handle_count == 1
            
        finally:
            await bus.stop()
    
    async def test_event_bus_stats(self):
        """Test event bus statistics."""
        bus = EventBus()
        handler = TestEventHandler()
        
        bus.subscribe("test.event", handler)
        await bus.start()
        
        try:
            stats = bus.get_stats()
            
            assert stats["running"] is True
            assert stats["queue_size"] == 0
            assert stats["worker_count"] == bus._max_workers
            assert stats["handlers_count"] == 1
            assert "test.event" in stats["handler_types"]
            
        finally:
            await bus.stop()
    
    async def test_handler_error_handling(self):
        """Test error handling in event handlers."""
        
        class FailingHandler(EventHandler):
            async def handle(self, event: BaseEvent) -> None:
                raise ValueError("Test error")
            
            def can_handle(self, event_type: str) -> bool:
                return event_type == "test.event"
        
        bus = EventBus()
        failing_handler = FailingHandler()
        success_handler = TestEventHandler()
        
        # Subscribe both handlers
        bus.subscribe("test.event", failing_handler)
        bus.subscribe("test.event", success_handler)
        await bus.start()
        
        try:
            # Publish event
            event = TestEvent("test data")
            await bus.publish(event)
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Success handler should still work despite failing handler
            assert success_handler.handle_count == 1
            
        finally:
            await bus.stop()


@pytest.mark.unit
@pytest.mark.asyncio
class TestGlobalEventBus:
    """Test global event bus functions."""
    
    async def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns the same instance."""
        # Clean up any existing bus
        await shutdown_event_bus()
        
        bus1 = await get_event_bus()
        bus2 = await get_event_bus()
        
        assert bus1 is bus2
        assert bus1._running
        
        await shutdown_event_bus()
    
    async def test_publish_event_convenience(self):
        """Test the publish_event convenience function."""
        await shutdown_event_bus()  # Clean slate
        
        handler = TestEventHandler()
        bus = await get_event_bus()
        bus.subscribe("test.event", handler)
        
        try:
            # Use convenience function
            event = TestEvent("convenience test")
            await publish_event(event)
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            assert handler.handle_count == 1
            assert handler.handled_events[0].data == "convenience test"
            
        finally:
            await shutdown_event_bus()


@pytest.mark.unit
class TestEventHandler:
    """Test event handler base class."""
    
    def test_handler_interface(self):
        """Test that handler implements required interface."""
        handler = TestEventHandler()
        
        # Test can_handle method
        assert handler.can_handle("test.event")
        assert handler.can_handle("test.other")
        assert not handler.can_handle("other.event")
    
    async def test_handler_execution(self):
        """Test handler execution."""
        handler = TestEventHandler()
        event = TestEvent("handler test")
        
        await handler.handle(event)
        
        assert handler.handle_count == 1
        assert len(handler.handled_events) == 1
        assert handler.handled_events[0] is event