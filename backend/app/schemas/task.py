from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.schemas.base import AppBaseModel


class ModelInfo(AppBaseModel):
    id: str
    name: str
    provider: str
    enabled: bool = True


class ResponseOut(AppBaseModel):
    id: int
    model_id: str
    content: str
    created_at: datetime


class TaskCreate(AppBaseModel):
    prompt: str
    model_ids: List[str]
    category: Optional[str] = None


class TaskImportItem(AppBaseModel):
    prompt: str
    model_ids: List[str]
    category: Optional[str] = None


class TaskImportRequest(AppBaseModel):
    tasks: List[TaskImportItem]


class TaskImportResponse(AppBaseModel):
    created: List[int]


class TaskOut(AppBaseModel):
    id: int
    prompt: str
    category: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    responses: List[ResponseOut]
    response_count: Optional[int] = None
    annotation_count: Optional[int] = None
    kappa: Optional[float] = None
