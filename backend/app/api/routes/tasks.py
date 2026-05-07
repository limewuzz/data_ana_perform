from __future__ import annotations

import asyncio
import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin
from app.models.model_config import ModelConfig
from app.models.response import Response
from app.models.annotation import Annotation
from app.models.task import Task
from app.schemas.task import ResponseOut, TaskCreate, TaskImportRequest, TaskImportResponse, TaskOut
from app.services.model_calling import call_model
from app.services.task_metrics import infer_category, task_kappa

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _task_out(db: Session, task: Task, responses: list[Response]) -> TaskOut:
    return TaskOut(
        id=task.id,
        prompt=task.prompt,
        category=infer_category(task.prompt, task.category),
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        responses=[
            ResponseOut(id=r.id, model_id=r.model_id, content=r.content, created_at=r.created_at) for r in responses
        ],
        response_count=len(responses),
        annotation_count=db.scalar(select(func.count()).select_from(Annotation).where(Annotation.task_id == task.id)) or 0,
        kappa=task_kappa(db, task.id),
    )


async def _create_task(payload: TaskCreate, db: Session) -> TaskOut:
    if len(payload.model_ids) < 2:
        raise HTTPException(status_code=400, detail="model_ids must have at least 2 items")

    models = db.scalars(
        select(ModelConfig).where(ModelConfig.model_id.in_(payload.model_ids), ModelConfig.enabled == True)
    ).all()
    found = {m.model_id for m in models}
    missing = [mid for mid in payload.model_ids if mid not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"unknown or disabled model_ids: {missing}")

    task = Task(prompt=payload.prompt, category=payload.category, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)

    results = await asyncio.gather(*[call_model(model=m, prompt=payload.prompt) for m in models], return_exceptions=True)

    responses: list[Response] = []
    for m, res in zip(models, results):
        if isinstance(res, Exception):
            content = f"[error:{m.model_id}] {type(res).__name__}"
        else:
            content = res
        responses.append(Response(task_id=task.id, model_id=m.model_id, content=content))

    random.shuffle(responses)
    db.add_all(responses)
    db.commit()

    persisted = db.scalars(select(Response).where(Response.task_id == task.id)).all()
    random.shuffle(persisted)
    return _task_out(db, task, persisted)


@router.post("", response_model=TaskOut)
async def create_task(payload: TaskCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return await _create_task(payload, db)


@router.post("/import", response_model=TaskImportResponse)
async def import_tasks(payload: TaskImportRequest, db: Session = Depends(get_db), _user=Depends(require_admin)):
    created: list[int] = []
    for item in payload.tasks:
        task = await _create_task(TaskCreate(prompt=item.prompt, model_ids=item.model_ids, category=item.category), db)
        created.append(task.id)
    return TaskImportResponse(created=created)


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = select(Task).order_by(Task.id.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(Task.status == status)
    if category:
        q = q.where(Task.category == category)
    tasks = db.scalars(q).all()
    result: list[TaskOut] = []
    for t in tasks:
        rs = db.scalars(select(Response).where(Response.task_id == t.id)).all()
        result.append(_task_out(db, t, rs))
    return result


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    rs = db.scalars(select(Response).where(Response.task_id == task.id)).all()
    return _task_out(db, task, rs)
