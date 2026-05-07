from __future__ import annotations

from typing import Dict, List, Optional

from app.schemas.base import AppBaseModel


class ReviewTaskItem(AppBaseModel):
    task_id: int
    kappa: Optional[float] = None
    prompt: str
    status: str
    review_status: str


class LowKappaSet(AppBaseModel):
    threshold: float
    items: List[ReviewTaskItem]


class DropReasonStats(AppBaseModel):
    counts: Dict[str, int]


class ReviewActionRequest(AppBaseModel):
    action: str


class NeedsReworkSet(AppBaseModel):
    items: List[ReviewTaskItem]


class ReviewAnnotatorItem(AppBaseModel):
    annotator_id: int
    task_count: int
    annotation_count: int
    drop_rate: float
    avg_duration_ms: Optional[float] = None
    avg_kappa_with_others: Optional[float] = None
    flags: List[str]


class AnnotatorAnomalySet(AppBaseModel):
    drop_rate_gte: float
    avg_kappa_lte: Optional[float] = None
    avg_duration_ms_gte: Optional[int] = None
    min_task_count: int
    items: List[ReviewAnnotatorItem]


class LowMarginTaskItem(AppBaseModel):
    task_id: int
    prompt: str
    status: str
    review_status: str
    small_margin_ratio: float
    pair_count: int


class LowMarginSet(AppBaseModel):
    threshold: float
    ratio_gte: float
    items: List[LowMarginTaskItem]


class SlowTaskItem(AppBaseModel):
    task_id: int
    prompt: str
    status: str
    review_status: str
    avg_duration_ms: float


class SlowTaskSet(AppBaseModel):
    avg_duration_ms_gte: int
    items: List[SlowTaskItem]


class AnnotatorInconsistencyItem(AppBaseModel):
    annotator_id: int
    conflict_pairs: int
    total_pairs: int
    conflict_rate: float


class AnnotatorInconsistencySet(AppBaseModel):
    min_conflict_pairs: int
    items: List[AnnotatorInconsistencyItem]
