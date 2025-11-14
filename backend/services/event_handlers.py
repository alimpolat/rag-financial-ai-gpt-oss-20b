"""
Event handlers for processing domain events.
"""
from typing import Dict, Any
import time

from core.events import (
    BaseEvent, EventHandler,
    DocumentUploadedEvent, DocumentProcessingStartedEvent, 
    DocumentProcessingCompletedEvent, DocumentProcessingFailedEvent,
    ChatMessageReceivedEvent, ChatMessageProcessedEvent,
    SystemErrorEvent, SystemHealthCheckEvent
)
from core.logging import get_logger, log_with_context
from repositories.document_repository import DocumentRepository
from repositories.chat_repository import ChatSessionRepository, ChatMessageRepository

logger = get_logger("event_handlers")


class DocumentEventHandler(EventHandler):
    """Handler for document-related events."""
    
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
    
    async def handle(self, event: BaseEvent) -> None:
        """Handle document events."""
        
        if isinstance(event, DocumentUploadedEvent):
            await self._handle_document_uploaded(event)
        elif isinstance(event, DocumentProcessingStartedEvent):
            await self._handle_processing_started(event)
        elif isinstance(event, DocumentProcessingCompletedEvent):
            await self._handle_processing_completed(event)
        elif isinstance(event, DocumentProcessingFailedEvent):
            await self._handle_processing_failed(event)
    
    def can_handle(self, event_type: str) -> bool:
        """Check if this handler can handle the event type."""
        return event_type.startswith("document.")
    
    async def _handle_document_uploaded(self, event: DocumentUploadedEvent) -> None:
        """Handle document uploaded event."""
        log_with_context(
            logger,
            "info",
            "Document uploaded",
            document_id=event.document_id,
            filename=event.filename,
            file_size=event.file_size,
            correlation_id=event.correlation_id
        )
        
        # Additional processing could go here
        # e.g., virus scanning, format validation, etc.
    
    async def _handle_processing_started(self, event: DocumentProcessingStartedEvent) -> None:
        """Handle document processing started event."""
        log_with_context(
            logger,
            "info",
            "Document processing started",
            document_id=event.document_id,
            filename=event.filename,
            correlation_id=event.correlation_id
        )
        
        # Update document status to processing
        try:
            await self.document_repository.update(
                event.document_id, 
                {"status": "processing"}
            )
        except Exception as e:
            logger.error(f"Failed to update document status: {e}")
    
    async def _handle_processing_completed(self, event: DocumentProcessingCompletedEvent) -> None:
        """Handle document processing completed event."""
        log_with_context(
            logger,
            "info",
            "Document processing completed",
            document_id=event.document_id,
            filename=event.filename,
            chunk_count=event.chunk_count,
            processing_time=event.processing_time,
            correlation_id=event.correlation_id
        )
        
        # Update document status and chunk count
        try:
            await self.document_repository.mark_as_processed(
                event.document_id,
                event.chunk_count
            )
        except Exception as e:
            logger.error(f"Failed to mark document as processed: {e}")
    
    async def _handle_processing_failed(self, event: DocumentProcessingFailedEvent) -> None:
        """Handle document processing failed event."""
        log_with_context(
            logger,
            "error",
            "Document processing failed",
            document_id=event.document_id,
            filename=event.filename,
            error_message=event.error_message,
            error_type=event.error_type,
            processing_time=event.processing_time,
            correlation_id=event.correlation_id
        )
        
        # Update document status to failed
        try:
            await self.document_repository.mark_as_failed(
                event.document_id,
                event.error_message
            )
        except Exception as e:
            logger.error(f"Failed to mark document as failed: {e}")


class ChatEventHandler(EventHandler):
    """Handler for chat-related events."""
    
    def __init__(
        self, 
        chat_session_repository: ChatSessionRepository,
        chat_message_repository: ChatMessageRepository
    ):
        self.chat_session_repository = chat_session_repository
        self.chat_message_repository = chat_message_repository
    
    async def handle(self, event: BaseEvent) -> None:
        """Handle chat events."""
        
        if isinstance(event, ChatMessageReceivedEvent):
            await self._handle_message_received(event)
        elif isinstance(event, ChatMessageProcessedEvent):
            await self._handle_message_processed(event)
    
    def can_handle(self, event_type: str) -> bool:
        """Check if this handler can handle the event type."""
        return event_type.startswith("chat.")
    
    async def _handle_message_received(self, event: ChatMessageReceivedEvent) -> None:
        """Handle chat message received event."""
        log_with_context(
            logger,
            "info",
            "Chat message received",
            session_id=event.session_id,
            message_id=event.message_id,
            user_id=event.user_id,
            correlation_id=event.correlation_id
        )
        
        # Update session activity
        try:
            await self.chat_session_repository.increment_message_count(event.session_id)
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
    
    async def _handle_message_processed(self, event: ChatMessageProcessedEvent) -> None:
        """Handle chat message processed event."""
        log_with_context(
            logger,
            "info",
            "Chat message processed",
            session_id=event.session_id,
            message_id=event.message_id,
            processing_time=event.processing_time,
            confidence=event.confidence,
            sources_count=len(event.sources),
            correlation_id=event.correlation_id
        )
        
        # Store message in repository
        try:
            from repositories.base import ChatMessage
            from datetime import datetime
            
            chat_message = ChatMessage(
                message_id=event.message_id,
                session_id=event.session_id,
                user_message=event.user_message,
                ai_response=event.ai_response,
                sources=event.sources,
                confidence=event.confidence,
                processing_time=event.processing_time,
                created_at=datetime.utcnow().isoformat()
            )
            
            await self.chat_message_repository.create(chat_message)
        except Exception as e:
            logger.error(f"Failed to store chat message: {e}")


class SystemEventHandler(EventHandler):
    """Handler for system-level events."""
    
    def __init__(self):
        self.error_count = 0
        self.last_health_check = None
    
    async def handle(self, event: BaseEvent) -> None:
        """Handle system events."""
        
        if isinstance(event, SystemErrorEvent):
            await self._handle_system_error(event)
        elif isinstance(event, SystemHealthCheckEvent):
            await self._handle_health_check(event)
    
    def can_handle(self, event_type: str) -> bool:
        """Check if this handler can handle the event type."""
        return event_type.startswith("system.")
    
    async def _handle_system_error(self, event: SystemErrorEvent) -> None:
        """Handle system error event."""
        self.error_count += 1
        
        log_with_context(
            logger,
            "error",
            "System error occurred",
            service_name=event.service_name,
            error_type=event.error_type,
            error_message=event.error_message,
            total_error_count=self.error_count,
            correlation_id=event.correlation_id
        )
        
        # Could implement alerting logic here
        # e.g., send to Sentry, PagerDuty, etc.
        if self.error_count > 10:  # Threshold for critical errors
            logger.critical(f"High error rate detected: {self.error_count} errors")
    
    async def _handle_health_check(self, event: SystemHealthCheckEvent) -> None:
        """Handle system health check event."""
        self.last_health_check = event.timestamp
        
        log_with_context(
            logger,
            "info",
            "Health check completed",
            service_name=event.service_name,
            status=event.status,
            response_time=event.response_time,
            correlation_id=event.correlation_id
        )
        
        # Store health metrics for monitoring
        if event.status != "healthy":
            logger.warning(f"Service {event.service_name} is unhealthy: {event.details}")


class MetricsEventHandler(EventHandler):
    """Handler for collecting metrics from events."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "document_uploads": 0,
            "document_processing_time": [],
            "chat_messages": 0,
            "chat_processing_time": [],
            "system_errors": 0,
            "event_counts": {}
        }
    
    async def handle(self, event: BaseEvent) -> None:
        """Handle events for metrics collection."""
        
        # Count events by type
        event_type = event.event_type
        self.metrics["event_counts"][event_type] = (
            self.metrics["event_counts"].get(event_type, 0) + 1
        )
        
        # Specific metrics
        if isinstance(event, DocumentUploadedEvent):
            self.metrics["document_uploads"] += 1
        
        elif isinstance(event, DocumentProcessingCompletedEvent):
            self.metrics["document_processing_time"].append(event.processing_time)
            # Keep only last 100 measurements
            if len(self.metrics["document_processing_time"]) > 100:
                self.metrics["document_processing_time"] = (
                    self.metrics["document_processing_time"][-100:]
                )
        
        elif isinstance(event, ChatMessageReceivedEvent):
            self.metrics["chat_messages"] += 1
        
        elif isinstance(event, ChatMessageProcessedEvent):
            self.metrics["chat_processing_time"].append(event.processing_time)
            # Keep only last 100 measurements
            if len(self.metrics["chat_processing_time"]) > 100:
                self.metrics["chat_processing_time"] = (
                    self.metrics["chat_processing_time"][-100:]
                )
        
        elif isinstance(event, SystemErrorEvent):
            self.metrics["system_errors"] += 1
    
    def can_handle(self, event_type: str) -> bool:
        """This handler processes all events for metrics."""
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        metrics = self.metrics.copy()
        
        # Calculate averages
        if self.metrics["document_processing_time"]:
            metrics["avg_document_processing_time"] = (
                sum(self.metrics["document_processing_time"]) / 
                len(self.metrics["document_processing_time"])
            )
        
        if self.metrics["chat_processing_time"]:
            metrics["avg_chat_processing_time"] = (
                sum(self.metrics["chat_processing_time"]) / 
                len(self.metrics["chat_processing_time"])
            )
        
        return metrics


class AuditEventHandler(EventHandler):
    """Handler for audit logging of important events."""
    
    def __init__(self):
        self.audit_events = [
            "document.uploaded",
            "document.deleted", 
            "chat.session.created",
            "system.error"
        ]
    
    async def handle(self, event: BaseEvent) -> None:
        """Handle events that require audit logging."""
        
        if event.event_type in self.audit_events:
            await self._create_audit_log(event)
    
    def can_handle(self, event_type: str) -> bool:
        """Check if this event requires audit logging."""
        return event_type in self.audit_events
    
    async def _create_audit_log(self, event: BaseEvent) -> None:
        """Create audit log entry."""
        audit_data = {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "event_data": event.to_dict()
        }
        
        # In a real system, this would be stored in a secure audit database
        log_with_context(
            logger,
            "info",
            "Audit event logged",
            audit_data=audit_data,
            correlation_id=event.correlation_id
        )