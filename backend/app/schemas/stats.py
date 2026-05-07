from __future__ import annotations

from typing import List, Optional

from app.schemas.base import AppBaseModel


class TaskKappa(AppBaseModel):
    task_id: int
    kappa: Optional[float] = None


class CategoryKappaItem(AppBaseModel):
    category: str
    task_count: int
    kappa: Optional[float] = None


class CategoryDistributionItem(AppBaseModel):
    category: str
    task_count: int


class DistinctnessTaskItem(AppBaseModel):
    task_id: int
    similarity: float


class KappaStats(AppBaseModel):
    global_kappa: Optional[float] = None
    per_task: List[TaskKappa]
    per_category: List[CategoryKappaItem] = []


class AnnotatorStatsItem(AppBaseModel):
    annotator_id: int
    task_count: int
    avg_duration_ms: Optional[float] = None
    drop_rate: float
    avg_kappa_with_others: Optional[float] = None
    position_bias: Optional[float] = None


class AnnotatorStats(AppBaseModel):
    items: List[AnnotatorStatsItem]


class DashboardOverview(AppBaseModel):
    total_tasks: int
    completed_tasks: int
    dropped_tasks: int
    drop_rate: float
    avg_duration_ms: Optional[float] = None
    global_kappa: Optional[float] = None
    usable_data_ratio: float = 0.0
    low_distinctness_ratio: float = 0.0


class DashboardStats(AppBaseModel):
    overview: DashboardOverview
    kappa_histogram: List[int]
    low_kappa_tasks: List[TaskKappa]
    category_distribution: List[CategoryDistributionItem] = []
    similarity_histogram: List[int] = []
    low_distinctness_tasks: List[DistinctnessTaskItem] = []
