from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.annotation import Annotation
from app.models.task import Task
from app.models.task_claim import TaskClaim
from app.schemas.queue import NextTaskRequest, NextTaskResponse, QueueHistoryItem, QueueHistoryResponse, QueueProgress
from app.schemas.task import ResponseOut, TaskOut
from app.services.task_status import recompute_task_status
from app.services.task_metrics import infer_category, task_kappa

router = APIRouter(prefix="/api/queue", tags=["queue"])


def _task_out(db: Session, task: Task) -> TaskOut:
    from app.models.response import Response

    rs = db.scalars(select(Response).where(Response.task_id == task.id)).all()
    return TaskOut(
        id=task.id,
        prompt=task.prompt,
        category=infer_category(task.prompt, task.category),
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        responses=[ResponseOut(id=r.id, model_id=r.model_id, content=r.content, created_at=r.created_at) for r in rs],
        response_count=len(rs),
        annotation_count=db.scalar(select(func.count()).select_from(Annotation).where(Annotation.task_id == task.id)) or 0,
        kappa=task_kappa(db, task.id),
    )


@router.post("/next", response_model=NextTaskResponse)
def next_task(payload: NextTaskRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    limit = max(1, min(200, payload.limit))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(0, payload.skip_recent_claim_window_minutes))

    base = select(Task).where(Task.status.in_(("pending", "annotating")), Task.review_status != "locked")
    if payload.category:
        base = base.where(Task.category == payload.category)
    if not payload.include_needs_rework:
        base = base.where(Task.review_status != "needs_rework")

    base = base.where(~exists().where(Annotation.task_id == Task.id, Annotation.annotator_id == user.id))
    base = base.where(~exists().where(TaskClaim.task_id == Task.id, TaskClaim.annotator_id == user.id, TaskClaim.claimed_at >= cutoff))

    tasks = db.scalars(base.order_by((Task.review_status == "needs_rework").desc(), Task.id.asc()).limit(limit)).all()

    task = tasks[0] if tasks else None
    if not task:
        return NextTaskResponse(task=None)
    return NextTaskResponse(task=_task_out(db, task))


@router.post("/claim/{task_id}")
def claim_task(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.review_status == "locked":
        raise HTTPException(status_code=409, detail="Task locked")
    if task.status == "completed":
        raise HTTPException(status_code=409, detail="Task completed")

    existing = db.scalars(select(TaskClaim).where(TaskClaim.task_id == task_id, TaskClaim.annotator_id == user.id)).first()
    if existing:
        return {"ok": True, "task_id": task_id}
    db.add(TaskClaim(task_id=task_id, annotator_id=user.id))
    if task.status == "pending":
        task.status = "annotating"
    db.commit()
    return {"ok": True, "task_id": task_id}


@router.post("/complete/{task_id}")
def complete_task(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    ann = db.scalars(select(Annotation.id).where(Annotation.task_id == task_id, Annotation.annotator_id == user.id)).first()
    if not ann:
        raise HTTPException(status_code=409, detail="No annotation for this task by current user")

    status = recompute_task_status(db, task_id)
    db.commit()
    return {"ok": True, "task_id": task_id, "status": status}


@router.get("/progress", response_model=QueueProgress)
def queue_progress(db: Session = Depends(get_db), user=Depends(get_current_user)):
    total_tasks = db.scalar(select(func.count()).select_from(Task).where(Task.status != "dropped")) or 0
    annotated_tasks = (
        db.scalar(
            select(func.count(func.distinct(Annotation.task_id))).where(Annotation.annotator_id == user.id, Annotation.is_dropped == False)
        )
        or 0
    )
    remaining_tasks = max(0, total_tasks - annotated_tasks)
    return QueueProgress(total_tasks=total_tasks, annotated_tasks=annotated_tasks, remaining_tasks=remaining_tasks)


@router.get("/history", response_model=QueueHistoryResponse)
def queue_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    limit = max(1, min(200, limit))
    offset = max(0, offset)
    anns = db.scalars(
        select(Annotation)
        .where(Annotation.annotator_id == user.id)
        .order_by(Annotation.created_at.desc(), Annotation.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return QueueHistoryResponse(items=[QueueHistoryItem(task_id=ann.task_id, created_at=ann.created_at) for ann in anns])
