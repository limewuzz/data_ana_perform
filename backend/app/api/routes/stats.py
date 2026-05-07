from __future__ import annotations

import json
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.annotation import Annotation
from app.models.response import Response
from app.models.task import Task
from app.schemas.stats import (
    AnnotatorStats,
    AnnotatorStatsItem,
    DistinctnessTaskItem,
    DashboardOverview,
    DashboardStats,
    KappaStats,
    TaskKappa,
)
from app.services.kappa import average_kappa_per_annotator, average_pairwise_kappa, labels_from_groups
from app.services.pairwise import to_groups
from app.services.task_metrics import (
    LOW_DISTINCTNESS_THRESHOLD,
    LOW_KAPPA_THRESHOLD,
    category_distribution,
    category_kappas,
    infer_category,
    initial_first_response_id,
    task_distinctness,
    task_is_usable,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _load_json(s: str | None):
    return json.loads(s) if s else None


def _task_labels(db: Session, task_id: int) -> Dict[int, list]:
    anns = db.scalars(
        select(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
    ).all()
    labels_by_annotator: Dict[int, list] = {}
    for a in anns:
        ranking = json.loads(a.ranking)
        ranking_groups = _load_json(a.ranking_groups)
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        labels_by_annotator[a.annotator_id] = labels_from_groups(groups)
    return labels_by_annotator


@router.get("/kappa", response_model=KappaStats)
def kappa_stats(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    tasks = db.scalars(select(Task.id).where(Task.status != "dropped").order_by(Task.id.asc())).all()
    per_task: List[TaskKappa] = []
    global_labels_by_annotator: Dict[int, list] = defaultdict(list)

    for tid in tasks:
        labels_by_annotator = _task_labels(db, tid)
        k = average_pairwise_kappa(labels_by_annotator)
        per_task.append(TaskKappa(task_id=tid, kappa=k))
        for aid, labels in labels_by_annotator.items():
            global_labels_by_annotator[aid].extend(labels)

    global_kappa = average_pairwise_kappa(global_labels_by_annotator)
    return KappaStats(global_kappa=global_kappa, per_task=per_task, per_category=category_kappas(db))


@router.get("/annotators", response_model=AnnotatorStats)
def annotator_stats(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    anns = db.scalars(select(Annotation).order_by(Annotation.id.asc())).all()
    by_annotator: Dict[int, List[Annotation]] = defaultdict(list)
    for a in anns:
        by_annotator[a.annotator_id].append(a)

    global_labels_by_annotator: Dict[int, list] = defaultdict(list)
    for a in anns:
        if a.is_dropped:
            continue
        ranking = json.loads(a.ranking)
        ranking_groups = _load_json(a.ranking_groups)
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        global_labels_by_annotator[a.annotator_id].extend(labels_from_groups(groups))

    avg_kappa = average_kappa_per_annotator(global_labels_by_annotator)
    position_bias_hits: Dict[int, int] = defaultdict(int)
    position_bias_total: Dict[int, int] = defaultdict(int)

    items: List[AnnotatorStatsItem] = []
    response_count_cache: Dict[int, int] = {}
    first_response_cache: Dict[int, Optional[int]] = {}
    for ann in anns:
        if ann.is_dropped:
            continue
        ranking = json.loads(ann.ranking)
        if not ranking:
            continue
        if ann.task_id not in response_count_cache:
            response_count_cache[ann.task_id] = (
                db.scalar(select(func.count()).select_from(Response).where(Response.task_id == ann.task_id)) or 0
            )
        if ann.task_id not in first_response_cache:
            first_response_cache[ann.task_id] = initial_first_response_id(db, ann.task_id)
        initial_first = first_response_cache[ann.task_id]
        if not initial_first or response_count_cache[ann.task_id] <= 0:
            continue
        position_bias_total[ann.annotator_id] += 1
        if ranking[0] == initial_first:
            position_bias_hits[ann.annotator_id] += 1

    for aid, lst in sorted(by_annotator.items(), key=lambda x: x[0]):
        durations = [a.duration_ms for a in lst if a.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else None
        drop_count = sum(1 for a in lst if a.is_dropped)
        task_count = len({a.task_id for a in lst})
        drop_rate = drop_count / len(lst) if lst else 0.0
        annotated_non_dropped = [a for a in lst if not a.is_dropped]
        baseline = 0.0
        if annotated_non_dropped:
            response_sizes = [
                response_count_cache.get(a.task_id)
                or db.scalar(select(func.count()).select_from(Response).where(Response.task_id == a.task_id))
                or 0
                for a in annotated_non_dropped
            ]
            bases = [1.0 / size for size in response_sizes if size and size > 0]
            baseline = sum(bases) / len(bases) if bases else 0.0
        observed = (
            position_bias_hits[aid] / position_bias_total[aid] if position_bias_total.get(aid, 0) > 0 else None
        )
        position_bias = None if observed is None else observed - baseline
        items.append(
            AnnotatorStatsItem(
                annotator_id=aid,
                task_count=task_count,
                avg_duration_ms=avg_duration,
                drop_rate=drop_rate,
                avg_kappa_with_others=avg_kappa.get(aid),
                position_bias=position_bias,
            )
        )
    return AnnotatorStats(items=items)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    tasks = db.scalars(select(Task).order_by(Task.id.asc())).all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for task in tasks if task.status == "completed")
    dropped_tasks = sum(1 for task in tasks if task.status == "dropped")
    drop_rate = dropped_tasks / total_tasks if total_tasks else 0.0

    durations = db.scalars(select(Annotation.duration_ms).where(Annotation.duration_ms.is_not(None))).all()
    duration_vals = [d for d in durations if d is not None]
    avg_duration = sum(duration_vals) / len(duration_vals) if duration_vals else None

    kappa = kappa_stats(db=db, _user=_user)
    global_kappa = kappa.global_kappa

    bins = [0] * 10
    low_tasks: List[TaskKappa] = []
    for t in kappa.per_task:
        if t.kappa is None:
            continue
        idx = int(min(9, max(0, t.kappa * 10)))
        bins[idx] += 1
        if t.kappa < LOW_KAPPA_THRESHOLD:
            low_tasks.append(t)

    category_items = category_distribution(tasks)
    similarity_histogram = [0] * 10
    low_distinctness_tasks: List[DistinctnessTaskItem] = []
    usable_tasks = 0
    for task in tasks:
        if task_is_usable(db, task):
            usable_tasks += 1
        similarity = task_distinctness(db, task.id)
        if similarity is None:
            continue
        idx = int(min(9, max(0, similarity * 10)))
        similarity_histogram[idx] += 1
        if similarity > LOW_DISTINCTNESS_THRESHOLD:
            low_distinctness_tasks.append(DistinctnessTaskItem(task_id=task.id, similarity=similarity))

    usable_data_ratio = usable_tasks / total_tasks if total_tasks else 0.0
    low_distinctness_ratio = (
        len(low_distinctness_tasks) / len([task for task in tasks if task.status != "dropped"])
        if any(task.status != "dropped" for task in tasks)
        else 0.0
    )

    overview = DashboardOverview(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        dropped_tasks=dropped_tasks,
        drop_rate=drop_rate,
        avg_duration_ms=avg_duration,
        global_kappa=global_kappa,
        usable_data_ratio=usable_data_ratio,
        low_distinctness_ratio=low_distinctness_ratio,
    )
    return DashboardStats(
        overview=overview,
        kappa_histogram=bins,
        low_kappa_tasks=low_tasks,
        category_distribution=category_items,
        similarity_histogram=similarity_histogram,
        low_distinctness_tasks=low_distinctness_tasks,
    )
