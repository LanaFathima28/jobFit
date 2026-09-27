from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from celery.result import AsyncResult

from app.core.security import verify_api_key
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["Async Tasks"])


class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="Unique Celery task identifier")
    status: str = Field(..., description="Task status: pending, processing, success, or failed")
    step: Optional[str] = Field(None, description="Current workflow step name")
    progress: int = Field(0, description="Task completion percentage (0-100)")
    details: Optional[Dict[str, Any]] = Field(None, description="Task execution details or intermediate results")
    result: Optional[Any] = Field(None, description="Final return value of the task if completed")
    error: Optional[str] = Field(None, description="Error message if the task failed")


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Get real-time execution status, progress, current step, and result of an async background task.
    """
    try:
        async_result = AsyncResult(task_id, app=celery_app)
        state = async_result.state
    except Exception as e:
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            step="processing",
            progress=50,
            details={"message": "Task status queried (Redis backend unreachable or offline)"}
        )

    # Handle Celery task states
    if state == "PENDING":
        return TaskStatusResponse(
            task_id=task_id,
            status="pending",
            step="queued",
            progress=0,
            details={"message": "Task is queued and waiting for worker"}
        )
    elif state in ["STARTED", "PROCESSING"]:
        meta = async_result.info if isinstance(async_result.info, dict) else {}
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            step=meta.get("step", "processing"),
            progress=meta.get("progress", 50),
            details=meta.get("details"),
            error=meta.get("error")
        )
    elif state == "SUCCESS":
        res = async_result.result
        details = res if isinstance(res, dict) else {"result": res}
        return TaskStatusResponse(
            task_id=task_id,
            status="success",
            step="completed",
            progress=100,
            details=details,
            result=res
        )
    elif state == "FAILURE":
        err_msg = str(async_result.result) if async_result.result else "Task execution failed"
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            step="failed",
            progress=0,
            error=err_msg
        )
    else:
        # Custom state or custom meta dict stored
        meta = async_result.info if isinstance(async_result.info, dict) else {}
        status_str = meta.get("status") or state.lower()
        return TaskStatusResponse(
            task_id=task_id,
            status=status_str if status_str in ["pending", "processing", "success", "failed"] else "processing",
            step=meta.get("step", "processing"),
            progress=meta.get("progress", 50),
            details=meta.get("details"),
            result=async_result.result if state == "SUCCESS" else None,
            error=meta.get("error") or (str(async_result.result) if state == "FAILURE" else None)
        )
