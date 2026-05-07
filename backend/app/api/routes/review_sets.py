from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_reviewer_or_admin
from app.models.annotation import Annotation
from app.models.response import Response
from app.models.review_event import ReviewEvent
from app.models.task import Task
from app.schemas.review import (
    AnnotatorInconsistencyItem,
    AnnotatorInconsistencySet,
    AnnotatorAnomalySet,
    DropReasonStats,
    LowMarginSet,
    LowMarginTaskItem,
    LowKappaSet,
    NeedsReworkSet,
    ReviewActionRequest,
    ReviewAnnotatorItem,
    ReviewTaskItem,
    SlowTaskItem,
    SlowTaskSet,
)
from app.schemas.review_event import ApplySetActionRequest, BulkReviewActionRequest, ReviewEventOut
from app.services.kappa import average_kappa_per_annotator, average_pairwise_kappa, labels_from_groups
from app.services.pairwise import to_groups

router = APIRouter(prefix="/api/review-sets", tags=["review-sets"])


def _load_json(s: Optional[str]):
    return json.loads(s) if s else None


def _task_kappa(db: Session, task_id: int) -> Optional[float]:
    anns = db.scalars(
        select(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
    ).all()
    labels_by_annotator: dict[int, list] = {}
    for a in anns:
        ranking = json.loads(a.ranking)
        ranking_groups = _load_json(a.ranking_groups)
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        labels_by_annotator[a.annotator_id] = labels_from_groups(groups)
    return average_pairwise_kappa(labels_by_annotator)


def _ordered_pair(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _task_margin_stats(db: Session, task_id: int, threshold: float) -> Tuple[float, int]:
    anns = db.scalars(
        select(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
    ).all()
    if not anns:
        return 0.0, 0

    responses = db.scalars(select(Response).where(Response.task_id == task_id)).all()
    by_id = {r.id: r for r in responses}

    small = 0
    total = 0
    for ann in anns:
        ranking: list[int] = json.loads(ann.ranking)
        ranking_groups = _load_json(ann.ranking_groups)
        scores = _load_json(ann.scores) or {}
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)

        group_index: dict[int, int] = {}
        for gi, g in enumerate(groups):
            for rid in g:
                group_index[rid] = gi
        g_count = len(groups)

        def get_score(rid: int):
            if str(rid) in scores:
                return scores[str(rid)]
            return scores.get(rid)

        for g in groups:
            if len(g) < 2:
                continue
            for i in range(len(g)):
                for j in range(i + 1, len(g)):
                    total += 1
                    if 0.0 <= threshold:
                        small += 1

        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                for a in groups[i]:
                    for b in groups[j]:
                        if a not in by_id or b not in by_id:
                            continue
                        cg = group_index.get(a, 0)
                        rg = group_index.get(b, cg)
                        rank_gap = (rg - cg) / max(1, g_count - 1)
                        cs = get_score(a)
                        rs = get_score(b)
                        score_gap = 0.0
                        if cs is not None and rs is not None:
                            score_gap = (float(cs) - float(rs)) / 4.0
                        margin = rank_gap + score_gap
                        total += 1
                        if abs(margin) <= threshold:
                            small += 1

    if total == 0:
        return 0.0, 0
    return small / total, total


def _write_review_event(db: Session, *, task_id: int, reviewer_id: int, action: str, reason: Optional[str], source_set: Optional[str]):
    db.add(ReviewEvent(task_id=task_id, reviewer_id=reviewer_id, action=action, reason=reason, source_set=source_set))


@router.get("/low-kappa", response_model=LowKappaSet)
def low_kappa_set(
    threshold: float = 0.4,
    limit: int = 100,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    tasks = db.scalars(select(Task).where(Task.status != "dropped").order_by(Task.id.asc()).limit(limit)).all()
    items: List[ReviewTaskItem] = []
    for t in tasks:
        k = _task_kappa(db, t.id)
        if k is None:
            continue
        if k < threshold:
            items.append(
                ReviewTaskItem(
                    task_id=t.id,
                    kappa=k,
                    prompt=t.prompt,
                    status=t.status,
                    review_status=t.review_status,
                )
            )
    items.sort(key=lambda x: (x.kappa if x.kappa is not None else 9), reverse=False)
    return LowKappaSet(threshold=threshold, items=items)


@router.get("/drop-reasons", response_model=DropReasonStats)
def drop_reasons(db: Session = Depends(get_db), _reviewer=Depends(require_reviewer_or_admin)):
    anns = db.scalars(select(Annotation.drop_reason).where(Annotation.is_dropped == True)).all()
    c = Counter()
    for r in anns:
        key = (r or "unknown").strip() or "unknown"
        c[key] += 1
    return DropReasonStats(counts=dict(c))


@router.get("/needs-rework", response_model=NeedsReworkSet)
def needs_rework_set(limit: int = 100, db: Session = Depends(get_db), _reviewer=Depends(require_reviewer_or_admin)):
    limit = max(1, min(500, limit))
    tasks = db.scalars(select(Task).where(Task.review_status == "needs_rework").order_by(Task.id.asc()).limit(limit)).all()
    items: List[ReviewTaskItem] = []
    for t in tasks:
        items.append(
            ReviewTaskItem(task_id=t.id, kappa=_task_kappa(db, t.id), prompt=t.prompt, status=t.status, review_status=t.review_status)
        )
    return NeedsReworkSet(items=items)


@router.get("/annotators/anomalies", response_model=AnnotatorAnomalySet)
def annotator_anomalies(
    drop_rate_gte: float = 0.5,
    avg_kappa_lte: Optional[float] = 0.4,
    avg_duration_ms_gte: Optional[int] = None,
    min_task_count: int = 1,
    include_all: bool = False,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    anns = db.scalars(select(Annotation).order_by(Annotation.id.asc())).all()
    by_annotator: Dict[int, List[Annotation]] = defaultdict(list)
    for a in anns:
        by_annotator[a.annotator_id].append(a)

    labels_by_annotator: Dict[int, list] = defaultdict(list)
    for a in anns:
        if a.is_dropped:
            continue
        ranking = json.loads(a.ranking)
        ranking_groups = _load_json(a.ranking_groups)
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        labels_by_annotator[a.annotator_id].extend(labels_from_groups(groups))

    kappas = average_kappa_per_annotator(labels_by_annotator)

    items: List[ReviewAnnotatorItem] = []
    for aid, lst in sorted(by_annotator.items(), key=lambda x: x[0]):
        task_count = len({a.task_id for a in lst})
        if task_count < min_task_count:
            continue
        annotation_count = len(lst)
        drop_count = sum(1 for a in lst if a.is_dropped)
        drop_rate = drop_count / annotation_count if annotation_count else 0.0
        durations = [a.duration_ms for a in lst if a.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else None
        avg_kappa = kappas.get(aid)

        flags: List[str] = []
        if drop_rate >= drop_rate_gte:
            flags.append("high_drop")
        if avg_kappa_lte is not None and avg_kappa is not None and avg_kappa <= avg_kappa_lte:
            flags.append("low_kappa")
        if avg_duration_ms_gte is not None and avg_duration is not None and avg_duration >= float(avg_duration_ms_gte):
            flags.append("slow")

        if include_all or flags:
            items.append(
                ReviewAnnotatorItem(
                    annotator_id=aid,
                    task_count=task_count,
                    annotation_count=annotation_count,
                    drop_rate=drop_rate,
                    avg_duration_ms=avg_duration,
                    avg_kappa_with_others=avg_kappa,
                    flags=flags,
                )
            )

    return AnnotatorAnomalySet(
        drop_rate_gte=drop_rate_gte,
        avg_kappa_lte=avg_kappa_lte,
        avg_duration_ms_gte=avg_duration_ms_gte,
        min_task_count=min_task_count,
        items=items,
    )


@router.get("/low-margin", response_model=LowMarginSet)
def low_margin_set(
    threshold: float = 0.1,
    ratio_gte: float = 0.6,
    limit: int = 200,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    limit = max(1, min(500, limit))
    tasks = db.scalars(select(Task).where(Task.status != "dropped").order_by(Task.id.asc()).limit(limit)).all()
    items: List[LowMarginTaskItem] = []
    for t in tasks:
        ratio, pair_count = _task_margin_stats(db, t.id, threshold)
        if pair_count == 0:
            continue
        if ratio >= ratio_gte:
            items.append(
                LowMarginTaskItem(
                    task_id=t.id,
                    prompt=t.prompt,
                    status=t.status,
                    review_status=t.review_status,
                    small_margin_ratio=ratio,
                    pair_count=pair_count,
                )
            )
    items.sort(key=lambda x: x.small_margin_ratio, reverse=True)
    return LowMarginSet(threshold=threshold, ratio_gte=ratio_gte, items=items)


@router.get("/slow-tasks", response_model=SlowTaskSet)
def slow_tasks_set(
    avg_duration_ms_gte: int = 10000,
    limit: int = 200,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    limit = max(1, min(500, limit))
    tasks = db.scalars(select(Task).order_by(Task.id.asc()).limit(limit)).all()
    items: List[SlowTaskItem] = []
    for t in tasks:
        durations = db.scalars(select(Annotation.duration_ms).where(Annotation.task_id == t.id, Annotation.duration_ms.is_not(None))).all()
        vals = [d for d in durations if d is not None]
        if not vals:
            continue
        avg = float(sum(vals)) / float(len(vals))
        if avg >= float(avg_duration_ms_gte):
            items.append(
                SlowTaskItem(task_id=t.id, prompt=t.prompt, status=t.status, review_status=t.review_status, avg_duration_ms=avg)
            )
    items.sort(key=lambda x: x.avg_duration_ms, reverse=True)
    return SlowTaskSet(avg_duration_ms_gte=avg_duration_ms_gte, items=items)


@router.get("/annotators/inconsistencies", response_model=AnnotatorInconsistencySet)
def annotator_inconsistencies_set(
    min_conflict_pairs: int = 1,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    anns = db.scalars(select(Annotation).where(Annotation.is_dropped == False).order_by(Annotation.id.asc())).all()
    per_task_responses: Dict[int, Dict[int, str]] = {}
    for a in anns:
        if a.task_id in per_task_responses:
            continue
        rs = db.scalars(select(Response).where(Response.task_id == a.task_id)).all()
        per_task_responses[a.task_id] = {r.id: r.model_id for r in rs}

    wins: Dict[int, Dict[Tuple[str, str], Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for a in anns:
        resp_map = per_task_responses.get(a.task_id, {})
        ranking: list[int] = json.loads(a.ranking)
        ranking_groups = _load_json(a.ranking_groups)
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                for rid_win in groups[i]:
                    for rid_lose in groups[j]:
                        mw = resp_map.get(rid_win)
                        ml = resp_map.get(rid_lose)
                        if not mw or not ml or mw == ml:
                            continue
                        a_id, b_id = _ordered_pair(mw, ml)
                        winner = mw
                        wins[a.annotator_id][(a_id, b_id)][winner] += 1

    items: List[AnnotatorInconsistencyItem] = []
    for aid, pairs in sorted(wins.items(), key=lambda x: x[0]):
        total_pairs = len(pairs)
        conflict_pairs = 0
        for (m1, m2), d in pairs.items():
            if d.get(m1, 0) > 0 and d.get(m2, 0) > 0:
                conflict_pairs += 1
        if conflict_pairs >= min_conflict_pairs:
            rate = float(conflict_pairs) / float(total_pairs) if total_pairs else 0.0
            items.append(
                AnnotatorInconsistencyItem(
                    annotator_id=aid, conflict_pairs=conflict_pairs, total_pairs=total_pairs, conflict_rate=rate
                )
            )
    items.sort(key=lambda x: x.conflict_rate, reverse=True)
    return AnnotatorInconsistencySet(min_conflict_pairs=min_conflict_pairs, items=items)


@router.post("/tasks/{task_id}/action")
def review_action(
    task_id: int,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    action = payload.action
    if action not in ("needs_rework", "locked", "none"):
        raise HTTPException(status_code=400, detail="invalid action")
    task.review_status = action
    _write_review_event(db, task_id=task_id, reviewer_id=_reviewer.id, action=action, reason=None, source_set=None)
    db.commit()
    return {"ok": True, "task_id": task_id, "review_status": task.review_status}


@router.post("/bulk-action")
def bulk_review_action(
    payload: BulkReviewActionRequest,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    action = payload.action
    if action not in ("needs_rework", "locked", "none"):
        raise HTTPException(status_code=400, detail="invalid action")
    task_ids = sorted(set(payload.task_ids))
    if not task_ids:
        raise HTTPException(status_code=400, detail="task_ids required")

    tasks = db.scalars(select(Task).where(Task.id.in_(task_ids))).all()
    found = {t.id for t in tasks}
    missing = [tid for tid in task_ids if tid not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"tasks not found: {missing}")

    for t in tasks:
        t.review_status = action
        _write_review_event(
            db,
            task_id=t.id,
            reviewer_id=_reviewer.id,
            action=action,
            reason=payload.reason,
            source_set=payload.source_set,
        )
    db.commit()
    return {"ok": True, "updated": len(tasks), "review_status": action}


@router.get("/events", response_model=list[ReviewEventOut])
def list_review_events(
    task_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    limit = max(1, min(200, limit))
    q = select(ReviewEvent).order_by(ReviewEvent.id.desc()).limit(limit)
    if task_id is not None:
        q = q.where(ReviewEvent.task_id == task_id)
    events = db.scalars(q).all()
    return [
        ReviewEventOut(
            id=e.id,
            task_id=e.task_id,
            reviewer_id=e.reviewer_id,
            action=e.action,
            reason=e.reason,
            source_set=e.source_set,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.post("/apply-set-action")
def apply_set_action(
    payload: ApplySetActionRequest,
    db: Session = Depends(get_db),
    _reviewer=Depends(require_reviewer_or_admin),
):
    params = payload.params or {}
    set_name = payload.set_name

    if set_name == "low-margin":
        threshold = float(params.get("threshold", 0.1))
        ratio_gte = float(params.get("ratio_gte", 0.6))
        limit = int(params.get("limit", 200))
        tasks = db.scalars(select(Task).where(Task.status != "dropped").order_by(Task.id.asc()).limit(limit)).all()
        task_ids = []
        for t in tasks:
            ratio, pair_count = _task_margin_stats(db, t.id, threshold)
            if pair_count > 0 and ratio >= ratio_gte:
                task_ids.append(t.id)
    elif set_name == "slow-tasks":
        avg_duration_ms_gte = int(params.get("avg_duration_ms_gte", 10000))
        limit = int(params.get("limit", 200))
        tasks = db.scalars(select(Task).order_by(Task.id.asc()).limit(limit)).all()
        task_ids = []
        for t in tasks:
            durations = db.scalars(
                select(Annotation.duration_ms).where(Annotation.task_id == t.id, Annotation.duration_ms.is_not(None))
            ).all()
            vals = [d for d in durations if d is not None]
            if not vals:
                continue
            avg = float(sum(vals)) / float(len(vals))
            if avg >= float(avg_duration_ms_gte):
                task_ids.append(t.id)
    elif set_name == "low-kappa":
        threshold = float(params.get("threshold", 0.4))
        limit = int(params.get("limit", 100))
        tasks = db.scalars(select(Task).where(Task.status != "dropped").order_by(Task.id.asc()).limit(limit)).all()
        task_ids = []
        for t in tasks:
            k = _task_kappa(db, t.id)
            if k is not None and k < threshold:
                task_ids.append(t.id)
    elif set_name == "needs-rework":
        limit = int(params.get("limit", 100))
        tasks = db.scalars(select(Task).where(Task.review_status == "needs_rework").order_by(Task.id.asc()).limit(limit)).all()
        task_ids = [t.id for t in tasks]
    else:
        raise HTTPException(status_code=400, detail="unknown set_name")

    if not task_ids:
        return {"ok": True, "dry_run": payload.dry_run, "task_ids": [], "updated": 0, "review_status": payload.action}

    if payload.dry_run:
        return {"ok": True, "dry_run": True, "task_ids": task_ids, "updated": 0, "review_status": payload.action}

    return bulk_review_action(
        BulkReviewActionRequest(task_ids=task_ids, action=payload.action, reason=payload.reason, source_set=set_name),
        db=db,
        _reviewer=_reviewer,
    )
