"""
Event system for async processing and decoupled communication.
"""
import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
import json

from core.logging import get_logger

logger = get_logger("events")

# Type variables
EventType = TypeVar('EventType', bound='BaseEvent')
HandlerType = Callable[[EventType], Any]


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class BaseEvent(ABC):
    """Base class for all events."""
    
    def __init__(self, 
                 event_id: Optional[str] = None,
                 timestamp: Optional[datetime] = None,
                 correlation_id: Optional[str] = None,
                 priority: EventPriority = EventPriority.NORMAL,
                 metadata: Optional[Dict[str, Any]] = None):
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.utcnow()
        self.correlation_id = correlation_id
        self.priority = priority
        self.metadata = metadata or {}
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the event type identifier."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "data": {k: v for k, v in self.__dict__.items() 
                    if k not in ['event_id', 'timestamp', 'correlation_id', 'priority', 'metadata']}
        }


# Authentication Events
class UserLoginEvent(BaseEvent):
    """Event fired when a user logs in."""
    
    def __init__(self,
                 user_id: str,
                 email: str,
                 ip_address: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.email = email
        self.ip_address = ip_address
    
    @property
    def event_type(self) -> str:
        return "user.login"


class UserLogoutEvent(BaseEvent):
    """Event fired when a user logs out."""
    
    def __init__(self,
                 user_id: str,
                 email: str,
                 **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.email = email
    
    @property
    def event_type(self) -> str:
        return "user.logout"


# Document Processing Events
class DocumentUploadedEvent(BaseEvent):
    """Event fired when a document is uploaded."""
    
    def __init__(self, 
                 document_id: str,
                 filename: str,
                 file_size: int,
                 file_type: str,
                 user_id: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.document_id = document_id
        self.filename = filename
        self.file_size = file_size
        self.file_type = file_type
        self.user_id = user_id
    
    @property
    def event_type(self) -> str:
        return "document.uploaded"


class DocumentProcessingStartedEvent(BaseEvent):
    """Event fired when document processing begins."""
    
    def __init__(self, 
                 document_id: str,
                 filename: str,
                 **kwargs):
        super().__init__(**kwargs)
        self.document_id = document_id
        self.filename = filename
    
    @property
    def event_type(self) -> str:
        return "document.processing.started"


class DocumentProcessingCompletedEvent(BaseEvent):
    """Event fired when document processing completes successfully."""
    
    def __init__(self, 
                 document_id: str,
                 filename: str,
                 chunk_count: int,
                 processing_time: float,
                 **kwargs):
        super().__init__(**kwargs)
        self.document_id = document_id
        self.filename = filename
        self.chunk_count = chunk_count
        self.processing_time = processing_time
    
    @property
    def event_type(self) -> str:
        return "document.processing.completed"


class DocumentProcessingFailedEvent(BaseEvent):
    """Event fired when document processing fails."""
    
    def __init__(self, 
                 document_id: str,
                 filename: str,
                 error_message: str,
                 error_type: str,
                 processing_time: float,
                 **kwargs):
        super().__init__(**kwargs)
        self.document_id = document_id
        self.filename = filename
        self.error_message = error_message
        self.error_type = error_type
        self.processing_time = processing_time
    
    @property
    def event_type(self) -> str:
        return "document.processing.failed"


class DocumentDeletedEvent(BaseEvent):
    """Event fired when a document is deleted."""
    
    def __init__(self, 
                 document_id: str,
                 filename: str,
                 user_id: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.document_id = document_id
        self.filename = filename
        self.user_id = user_id
    
    @property
    def event_type(self) -> str:
        return "document.deleted"


# Chat Events
class ChatMessageReceivedEvent(BaseEvent):
    """Event fired when a chat message is received."""
    
    def __init__(self, 
                 session_id: str,
                 message_id: str,
                 user_message: str,
                 user_id: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.message_id = message_id
        self.user_message = user_message
        self.user_id = user_id
    
    @property
    def event_type(self) -> str:
        return "chat.message.received"


class ChatMessageProcessedEvent(BaseEvent):
    """Event fired when a chat message is processed."""
    
    def __init__(self, 
                 session_id: str,
                 message_id: str,
                 user_message: str,
                 ai_response: str,
                 processing_time: float,
                 confidence: float,
                 sources: List[str],
                 **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.message_id = message_id
        self.user_message = user_message
        self.ai_response = ai_response
        self.processing_time = processing_time
        self.confidence = confidence
        self.sources = sources
    
    @property
    def event_type(self) -> str:
        return "chat.message.processed"


class ChatSessionCreatedEvent(BaseEvent):
    """Event fired when a new chat session is created."""
    
    def __init__(self, 
                 session_id: str,
                 user_id: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.user_id = user_id
    
    @property
    def event_type(self) -> str:
        return "chat.session.created"


# System Events
class SystemHealthCheckEvent(BaseEvent):
    """Event fired during system health checks."""
    
    def __init__(self, 
                 service_name: str,
                 status: str,
                 response_time: float,
                 details: Dict[str, Any],
                 **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name
        self.status = status
        self.response_time = response_time
        self.details = details
    
    @property
    def event_type(self) -> str:
        return "system.health.check"


class SystemErrorEvent(BaseEvent):
    """Event fired when system errors occur."""
    
    def __init__(self, 
                 error_message: str,
                 error_type: str,
                 service_name: str,
                 stack_trace: Optional[str] = None,
                 priority: EventPriority = EventPriority.HIGH,
                 **kwargs):
        super().__init__(priority=priority, **kwargs)
        self.error_message = error_message
        self.error_type = error_type
        self.service_name = service_name
        self.stack_trace = stack_trace
    
    @property
    def event_type(self) -> str:
        return "system.error"


class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: BaseEvent) -> None:
        """Handle the event."""
        pass
    
    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """Check if this handler can handle the given event type."""
        pass


class EventBus:
    """Central event bus for publishing and subscribing to events."""
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._worker_tasks: List[asyncio.Task] = []
        self._running = False
        self._max_workers = 5
        self._processed_events = 0
        self._failed_events = 0
    
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__class__.__name__} to {event_type}")
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"Unsubscribed handler {handler.__class__.__name__} from {event_type}")
            except ValueError:
                logger.warning(f"Handler {handler.__class__.__name__} not found for {event_type}")
    
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to the bus."""
        logger.info(f"Publishing event {event.event_type} with ID {event.event_id}")
        
        # Add to queue for processing
        await self._event_queue.put(event)
    
    async def start(self) -> None:
        """Start the event processing workers."""
        if self._running:
            return
        
        self._running = True
        logger.info(f"Starting event bus with {self._max_workers} workers")
        
        # Start worker tasks
        for i in range(self._max_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(task)
    
    async def stop(self) -> None:
        """Stop the event processing workers."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping event bus...")
        
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        
        logger.info(f"Event bus stopped. Processed: {self._processed_events}, Failed: {self._failed_events}")
    
    async def _worker(self, worker_name: str) -> None:
        """Worker coroutine to process events."""
        logger.info(f"Event worker {worker_name} started")
        
        try:
            while self._running:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                    await self._process_event(event, worker_name)
                    self._processed_events += 1
                    
                except asyncio.TimeoutError:
                    # No events to process, continue
                    continue
                except Exception as e:
                    logger.error(f"Error in event worker {worker_name}: {e}")
                    self._failed_events += 1
                    
        except asyncio.CancelledError:
            logger.info(f"Event worker {worker_name} cancelled")
        except Exception as e:
            logger.error(f"Fatal error in event worker {worker_name}: {e}")
    
    async def _process_event(self, event: BaseEvent, worker_name: str) -> None:
        """Process a single event."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get handlers for this event type
            handlers = self._handlers.get(event.event_type, [])
            
            if not handlers:
                logger.debug(f"No handlers for event type {event.event_type}")
                return
            
            # Process with all handlers
            tasks = []
            for handler in handlers:
                if handler.can_handle(event.event_type):
                    task = asyncio.create_task(self._handle_event_safely(handler, event))
                    tasks.append(task)
            
            if tasks:
                # Wait for all handlers to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any handler failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        handler_name = handlers[i].__class__.__name__
                        logger.error(f"Handler {handler_name} failed for event {event.event_id}: {result}")
            
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.debug(f"Processed event {event.event_id} in {processing_time:.3f}s by {worker_name}")
            
        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
    
    async def _handle_event_safely(self, handler: EventHandler, event: BaseEvent) -> None:
        """Safely handle an event with error recovery."""
        try:
            await handler.handle(event)
        except Exception as e:
            logger.error(f"Handler {handler.__class__.__name__} failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "running": self._running,
            "queue_size": self._event_queue.qsize(),
            "worker_count": len(self._worker_tasks),
            "handlers_count": sum(len(handlers) for handlers in self._handlers.values()),
            "processed_events": self._processed_events,
            "failed_events": self._failed_events,
            "handler_types": list(self._handlers.keys())
        }


# Global event bus instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _event_bus
    
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.start()
    
    return _event_bus


async def publish_event(event: BaseEvent) -> None:
    """Convenience function to publish an event."""
    bus = await get_event_bus()
    await bus.publish(event)


async def shutdown_event_bus() -> None:
    """Shutdown the global event bus."""
    global _event_bus
    
    if _event_bus:
        await _event_bus.stop()
        _event_bus = None