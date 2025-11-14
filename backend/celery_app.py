"""
Celery application for async task processing.
Handles background document processing and other long-running tasks.
"""
from celery import Celery, Task
from celery.signals import worker_ready, task_failure, task_success
import logging
import asyncio
from typing import Any, Dict
import time

from core.config import settings
from core.logging import get_logger

logger = get_logger("celery")

# Create Celery app
app = Celery(
    'rag_financial_ai',
    broker=settings.REDIS_URL or 'redis://localhost:6379/1',
    backend=settings.REDIS_URL.replace('/0', '/2') if settings.REDIS_URL else 'redis://localhost:6379/2',
    include=['tasks.document_tasks']
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Task execution settings
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=900,  # 15 minutes hard limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Routing
    task_routes={
        'tasks.document_tasks.*': {'queue': 'documents'},
        'tasks.embedding_tasks.*': {'queue': 'embeddings'},
        'tasks.notification_tasks.*': {'queue': 'notifications'},
    },
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        'cleanup-old-documents': {
            'task': 'tasks.document_tasks.cleanup_old_documents',
            'schedule': 86400.0,  # Daily
        },
        'refresh-cache': {
            'task': 'tasks.cache_tasks.refresh_popular_queries',
            'schedule': 3600.0,  # Hourly
        },
    },
)


class AsyncTask(Task):
    """Base task class that supports async functions."""
    
    def run(self, *args, **kwargs):
        """Run async task in event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_run(*args, **kwargs))
        finally:
            loop.close()
    
    async def async_run(self, *args, **kwargs):
        """Override this method in subclasses."""
        raise NotImplementedError()


@app.task(bind=True, name='tasks.health_check')
def health_check(self):
    """Health check task for monitoring."""
    return {
        'status': 'healthy',
        'worker_id': self.request.id,
        'timestamp': time.time()
    }


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handler for worker ready signal."""
    logger.info("Celery worker is ready and accepting tasks")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, 
                        args=None, kwargs=None, traceback=None, **kw):
    """Handler for task failure."""
    logger.error(f"Task {task_id} failed with exception: {exception}")
    logger.error(f"Traceback: {traceback}")


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handler for task success."""
    logger.debug(f"Task {sender.name} completed successfully")


if __name__ == '__main__':
    app.start()