from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.annotation import Annotation
from app.models.task import Task


def recompute_task_status(db: Session, task_id: int) -> str:
    task = db.get(Task, task_id)
    if not task:
        return "missing"

    total = db.scalar(select(func.count()).select_from(Annotation).where(Annotation.task_id == task_id)) or 0
    non_dropped = (
        db.scalar(
            select(func.count()).select_from(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == False)
        )
        or 0
    )
    dropped = (
        db.scalar(select(func.count()).select_from(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == True))
        or 0
    )

    target = settings.target_annotations_per_task

    if dropped > 0:
        task.status = "dropped"
    elif non_dropped >= target:
        task.status = "completed"
    elif total > 0:
        task.status = "annotating"
    else:
        task.status = "pending"

    return task.status
