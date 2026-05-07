from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.schemas.base import AppBaseModel


class ReviewEventOut(AppBaseModel):
    id: int
    task_id: int
    reviewer_id: int
    action: str
    reason: Optional[str] = None
    source_set: Optional[str] = None
    created_at: datetime


class BulkReviewActionRequest(AppBaseModel):
    task_ids: List[int]
    action: str
    reason: Optional[str] = None
    source_set: Optional[str] = None


class ApplySetActionRequest(AppBaseModel):
    set_name: str
    action: str
    reason: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    dry_run: bool = False
