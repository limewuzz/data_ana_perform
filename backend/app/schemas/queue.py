from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.schemas.base import AppBaseModel

from app.schemas.task import TaskOut


class NextTaskResponse(AppBaseModel):
    task: Optional[TaskOut] = None


class NextTaskRequest(AppBaseModel):
    category: Optional[str] = None
    limit: int = 50
    include_needs_rework: bool = True
    skip_recent_claim_window_minutes: int = 30


class QueueProgress(AppBaseModel):
    total_tasks: int
    annotated_tasks: int
    remaining_tasks: int


class QueueHistoryItem(AppBaseModel):
    task_id: int
    created_at: datetime


class QueueHistoryResponse(AppBaseModel):
    items: list[QueueHistoryItem]
