"""
Metrics endpoints for monitoring and observability.
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any

from core.dependencies import get_service_container
from core.logging import get_logger
from core.events import get_event_bus

router = APIRouter()
logger = get_logger("metrics_routes")


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get application metrics."""
    try:
        container = await get_service_container()
        event_bus = await get_event_bus()
        
        # Get metrics from event handler
        metrics_handler = container.metrics_event_handler
        application_metrics = metrics_handler.get_metrics()
        
        # Get event bus stats
        event_bus_stats = event_bus.get_stats()
        
        return {
            "application_metrics": application_metrics,
            "event_bus_stats": event_bus_stats,
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        return {
            "error": "Failed to retrieve metrics",
            "status": "error"
        }


@router.get("/metrics/events", response_model=Dict[str, Any])
async def get_event_metrics():
    """Get event-specific metrics."""
    try:
        event_bus = await get_event_bus()
        return event_bus.get_stats()
        
    except Exception as e:
        logger.error(f"Error retrieving event metrics: {e}")
        return {
            "error": "Failed to retrieve event metrics",
            "status": "error"
        }


@router.get("/metrics/performance", response_model=Dict[str, Any])
async def get_performance_metrics():
    """Get performance-related metrics."""
    try:
        container = await get_service_container()
        metrics_handler = container.metrics_event_handler
        metrics = metrics_handler.get_metrics()
        
        performance_metrics = {
            "document_processing": {
                "total_uploads": metrics.get("document_uploads", 0),
                "avg_processing_time": metrics.get("avg_document_processing_time", 0),
                "recent_processing_times": metrics.get("document_processing_time", [])[-10:]  # Last 10
            },
            "chat": {
                "total_messages": metrics.get("chat_messages", 0),
                "avg_processing_time": metrics.get("avg_chat_processing_time", 0),
                "recent_processing_times": metrics.get("chat_processing_time", [])[-10:]  # Last 10
            },
            "system": {
                "total_errors": metrics.get("system_errors", 0)
            }
        }
        
        return performance_metrics
        
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        return {
            "error": "Failed to retrieve performance metrics",
            "status": "error"
        }


@router.get("/metrics/health", response_model=Dict[str, Any])
async def get_health_metrics():
    """Get health-related metrics and status."""
    try:
        container = await get_service_container()
        event_bus = await get_event_bus()
        
        # Basic health indicators
        health_status = {
            "status": "healthy",
            "services": {
                "event_bus": "healthy" if event_bus.get_stats()["running"] else "unhealthy",
                "rag_service": "healthy",  # Could check actual service health
                "document_service": "healthy",
                "chat_service": "healthy"
            },
            "metrics": {
                "event_queue_size": event_bus.get_stats()["queue_size"],
                "active_workers": len([task for task in event_bus._worker_tasks if not task.done()]),
                "processed_events": event_bus.get_stats()["processed_events"],
                "failed_events": event_bus.get_stats()["failed_events"]
            }
        }
        
        # Determine overall health
        unhealthy_services = [
            service for service, status in health_status["services"].items() 
            if status != "healthy"
        ]
        
        if unhealthy_services:
            health_status["status"] = "unhealthy"
            health_status["unhealthy_services"] = unhealthy_services
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking health metrics: {e}")
        return {
            "status": "error",
            "error": "Failed to retrieve health metrics"
        }