from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.annotation import Annotation
from app.models.task import Task
from app.schemas.annotation import AnnotationCreate, AnnotationOut
from app.services.task_status import recompute_task_status

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


def _normalize_ranking(payload: AnnotationCreate) -> tuple[list[int], list[list[int]] | None]:
    if payload.ranking_groups:
        ranking_groups = payload.ranking_groups
        ranking = [rid for g in ranking_groups for rid in g]
        return ranking, ranking_groups
    if payload.ranking:
        return payload.ranking, None
    raise HTTPException(status_code=400, detail="ranking or ranking_groups required")


def _out(a: Annotation) -> AnnotationOut:
    return AnnotationOut(
        id=a.id,
        task_id=a.task_id,
        annotator_id=a.annotator_id,
        ranking=json.loads(a.ranking),
        ranking_groups=json.loads(a.ranking_groups) if a.ranking_groups else None,
        scores=json.loads(a.scores) if a.scores else None,
        edits=json.loads(a.edits) if a.edits else None,
        is_dropped=a.is_dropped,
        drop_reason=a.drop_reason,
        duration_ms=a.duration_ms,
        created_at=a.created_at,
    )


@router.post("", response_model=AnnotationOut)
def create_annotation(
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    task = db.get(Task, payload.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    existing = db.scalars(
        select(Annotation).where(Annotation.task_id == payload.task_id, Annotation.annotator_id == user.id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Annotation already exists for this task and user")

    ranking, ranking_groups = _normalize_ranking(payload)
    a = Annotation(
        task_id=payload.task_id,
        annotator_id=user.id,
        ranking=json.dumps(ranking),
        ranking_groups=json.dumps(ranking_groups) if ranking_groups else None,
        scores=json.dumps(payload.scores) if payload.scores else None,
        edits=json.dumps(payload.edits) if payload.edits else None,
        is_dropped=payload.is_dropped,
        drop_reason=payload.drop_reason,
        duration_ms=payload.duration_ms,
    )
    db.add(a)
    db.flush()

    recompute_task_status(db, task.id)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.get("", response_model=list[AnnotationOut])
def list_annotations(
    task_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    anns = db.scalars(select(Annotation).where(Annotation.task_id == task_id).order_by(Annotation.id.asc())).all()
    return [_out(a) for a in anns]
