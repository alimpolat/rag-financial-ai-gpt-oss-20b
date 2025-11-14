"""
WebSocket endpoints for real-time communication.
Handles live chat responses, document processing updates, and system notifications.
"""
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, Any, Optional, List
import json
import asyncio
import time
from datetime import datetime

from core.auth import get_current_user_optional, TokenData
from core.logging import get_logger
from services.cache_service import get_cache_service, CacheService
from celery.result import AsyncResult
from celery_app import app as celery_app

logger = get_logger("websocket")


class ConnectionManager:
    """Manages WebSocket connections for all clients."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_sessions: Dict[str, str] = {}  # websocket_id -> user_id mapping
    
    async def connect(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        
        self.active_connections[client_id].append(websocket)
        
        if user_id:
            self.user_sessions[id(websocket)] = user_id
        
        logger.info(f"WebSocket connected: {client_id} (user: {user_id})")
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        
        websocket_id = id(websocket)
        if websocket_id in self.user_sessions:
            del self.user_sessions[websocket_id]
        
        logger.info(f"WebSocket disconnected: {client_id}")
    
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    async def broadcast_to_client(self, client_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections for a client."""
        if client_id in self.active_connections:
            for websocket in self.active_connections[client_id]:
                await self.send_message(websocket, message)
    
    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections for a user."""
        for websocket_id, uid in self.user_sessions.items():
            if uid == user_id:
                for client_id, connections in self.active_connections.items():
                    for ws in connections:
                        if id(ws) == websocket_id:
                            await self.send_message(ws, message)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        for client_id in self.active_connections:
            await self.broadcast_to_client(client_id, message)


# Global connection manager
manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket) -> Optional[TokenData]:
    """
    Authenticate WebSocket connection using token from query params.
    
    Args:
        websocket: WebSocket connection
        
    Returns:
        User token data if authenticated, None otherwise
    """
    token = websocket.query_params.get("token")
    if not token:
        return None
    
    try:
        from core.auth import AuthService
        return AuthService.decode_token(token)
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        return None


async def handle_chat_message(
    websocket: WebSocket,
    message: Dict[str, Any],
    user: Optional[TokenData],
    cache_service: CacheService
):
    """
    Handle incoming chat messages.
    
    Args:
        websocket: WebSocket connection
        message: Chat message data
        user: Authenticated user data
        cache_service: Cache service instance
    """
    try:
        from services.rag_service import RAGService
        from services.chat_service import ChatService
        from core.dependencies import get_service_container
        
        # Get services
        container = await get_service_container()
        rag_service = container.get_rag_service()
        chat_service = container.get_chat_service()
        
        query = message.get("query", "")
        session_id = message.get("session_id")
        
        # Send acknowledgment
        await manager.send_message(websocket, {
            "type": "chat_status",
            "status": "processing",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Process query with streaming updates
        start_time = time.time()
        
        # Check cache first
        cached_result = await cache_service.get_query_result(query)
        if cached_result:
            await manager.send_message(websocket, {
                "type": "chat_response",
                "response": cached_result["response"],
                "sources": cached_result.get("sources", []),
                "confidence": cached_result.get("confidence", 0),
                "cached": True,
                "processing_time": time.time() - start_time,
                "timestamp": datetime.utcnow().isoformat()
            })
            return
        
        # Process with RAG
        result = await rag_service.process_query(query)
        
        # Send response
        await manager.send_message(websocket, {
            "type": "chat_response",
            "response": result["response"],
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0),
            "cached": False,
            "processing_time": time.time() - start_time,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Save to chat history if session exists
        if session_id and user:
            await chat_service.add_message(
                session_id=session_id,
                user_id=user.user_id,
                message=query,
                response=result["response"],
                sources=result.get("sources", [])
            )
        
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        await manager.send_message(websocket, {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_document_status(
    websocket: WebSocket,
    message: Dict[str, Any]
):
    """
    Handle document processing status requests.
    
    Args:
        websocket: WebSocket connection
        message: Status request message
    """
    try:
        task_id = message.get("task_id")
        if not task_id:
            await manager.send_message(websocket, {
                "type": "error",
                "error": "Missing task_id",
                "timestamp": datetime.utcnow().isoformat()
            })
            return
        
        # Get task status from Celery
        result = AsyncResult(task_id, app=celery_app)
        
        status_update = {
            "type": "document_status",
            "task_id": task_id,
            "status": result.state,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if result.info:
            status_update.update(result.info)
        
        if result.ready():
            status_update["ready"] = True
            status_update["successful"] = result.successful()
            if result.successful():
                status_update["result"] = result.result
        
        await manager.send_message(websocket, status_update)
        
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        await manager.send_message(websocket, {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


async def monitor_document_processing(
    websocket: WebSocket,
    task_id: str,
    interval: int = 2
):
    """
    Monitor document processing and send updates.
    
    Args:
        websocket: WebSocket connection
        task_id: Celery task ID
        interval: Update interval in seconds
    """
    try:
        while True:
            result = AsyncResult(task_id, app=celery_app)
            
            status_update = {
                "type": "document_progress",
                "task_id": task_id,
                "status": result.state,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if result.info:
                status_update.update(result.info)
            
            await manager.send_message(websocket, status_update)
            
            if result.ready():
                # Task completed
                final_update = {
                    "type": "document_complete",
                    "task_id": task_id,
                    "successful": result.successful(),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if result.successful():
                    final_update["result"] = result.result
                else:
                    final_update["error"] = str(result.info)
                
                await manager.send_message(websocket, final_update)
                break
            
            await asyncio.sleep(interval)
            
    except Exception as e:
        logger.error(f"Error monitoring document processing: {e}")
        await manager.send_message(websocket, {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Main WebSocket endpoint handler.
    
    Args:
        websocket: WebSocket connection
        client_id: Client identifier
        cache_service: Cache service instance
    """
    # Authenticate if token provided
    user = await authenticate_websocket(websocket)
    
    # Connect
    await manager.connect(websocket, client_id, user.user_id if user else None)
    
    # Send connection confirmation
    await manager.send_message(websocket, {
        "type": "connection",
        "status": "connected",
        "client_id": client_id,
        "authenticated": user is not None,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            logger.debug(f"Received WebSocket message: {message_type}")
            
            # Route message to appropriate handler
            if message_type == "chat":
                await handle_chat_message(websocket, data, user, cache_service)
            
            elif message_type == "document_status":
                await handle_document_status(websocket, data)
            
            elif message_type == "monitor_document":
                task_id = data.get("task_id")
                if task_id:
                    asyncio.create_task(
                        monitor_document_processing(websocket, task_id)
                    )
            
            elif message_type == "ping":
                await manager.send_message(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                await manager.send_message(websocket, {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_id)
        await websocket.close()


async def broadcast_system_notification(
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
):
    """
    Broadcast system-wide notification.
    
    Args:
        notification_type: Type of notification
        message: Notification message
        data: Additional data
    """
    notification = {
        "type": "system_notification",
        "notification_type": notification_type,
        "message": message,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_to_all(notification)