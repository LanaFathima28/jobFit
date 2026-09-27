from typing import Any, Dict, Optional
from celery import Celery
from app.core.config import settings

# Initialize Celery app instance for batch processing
celery_app = Celery(
    "jobfit_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_extended=True
)


def update_task_progress(
    task_obj: Any,
    state: str = "PROCESSING",
    step: str = "processing",
    progress: int = 0,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """
    Helper function to update Celery task state and meta dictionary in Redis backend.
    """
    meta = {
        "status": state.lower(),
        "step": step,
        "progress": progress,
        "details": details or {},
        "error": error
    }
    task_id = getattr(getattr(task_obj, "request", None), "id", None)
    if hasattr(task_obj, "update_state") and task_id:
        try:
            task_obj.update_state(state=state, meta=meta)
        except Exception:
            pass
    return meta


@celery_app.task(name="app.worker.ping")
def ping_task() -> str:
    """
    Simple worker health ping task.
    """
    return "pong"
