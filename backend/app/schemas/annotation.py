from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from app.schemas.base import AppBaseModel


class AnnotationCreate(AppBaseModel):
    task_id: int
    ranking: Optional[List[int]] = None
    ranking_groups: Optional[List[List[int]]] = None
    scores: Optional[Dict[int, int]] = None
    edits: Optional[Dict[int, str]] = None
    is_dropped: bool = False
    drop_reason: Optional[str] = None
    duration_ms: Optional[int] = None


class AnnotationOut(AppBaseModel):
    id: int
    task_id: int
    annotator_id: int
    ranking: List[int]
    ranking_groups: Optional[List[List[int]]]
    scores: Optional[Dict[int, int]]
    edits: Optional[Dict[int, str]]
    is_dropped: bool
    drop_reason: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime
