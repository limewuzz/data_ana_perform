from __future__ import annotations

import csv
import json
import os
import pathlib
import uuid
from io import StringIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.annotation import Annotation
from app.models.export_job import ExportJob
from app.models.response import Response
from app.models.task import Task
from app.schemas.export_job import ExportJobOut
from app.schemas.export import ExportRequest
from app.services.kappa import average_pairwise_kappa, labels_from_groups
from app.services.pairwise import pairwise_from_groups, to_groups

router = APIRouter(prefix="/api/export", tags=["export"])


def _safe_json_loads(s: str | None):
    if not s:
        return None
    return json.loads(s)


def _export_dir() -> pathlib.Path:
    d = pathlib.Path(__file__).resolve().parents[3] / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _build_records_for_task(
    *,
    task: Task,
    annotations: list[Annotation],
    responses: list[Response],
    payload: ExportRequest,
    export_job_id: str,
) -> list[dict]:
    by_id = {r.id: r for r in responses}
    records: list[dict] = []

    for ann in annotations:
        ranking: list[int] = json.loads(ann.ranking)
        ranking_groups = _safe_json_loads(ann.ranking_groups)
        scores = _safe_json_loads(ann.scores) or {}
        edits = _safe_json_loads(ann.edits) or {}

        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        seed = payload.tie_seed or f"{export_job_id}:{task.id}:{ann.annotator_id}"
        pairs = pairwise_from_groups(groups=groups, tie_handling=payload.tie_handling, seed=seed)

        group_index: dict[int, int] = {}
        for gi, g in enumerate(groups):
            for rid in g:
                group_index[rid] = gi

        g_count = len(groups)

        def get_content(rid: int) -> str:
            if payload.use_edits and str(rid) in edits:
                return edits[str(rid)]
            if payload.use_edits and rid in edits:
                return edits[rid]
            r = by_id.get(rid)
            return r.content if r else ""

        def get_score(rid: int):
            if str(rid) in scores:
                return scores[str(rid)]
            return scores.get(rid)

        if payload.format == "alpaca":
            top = groups[0] if groups else []
            if not top:
                continue
            pick = top[0]
            if len(top) > 1:
                import hashlib
                import random

                h = hashlib.sha256(seed.encode("utf-8")).digest()
                n = int.from_bytes(h[:8], "big", signed=False)
                rng = random.Random(n)
                pick = rng.choice(top)
            records.append({"instruction": task.prompt, "input": "", "output": get_content(pick)})
            continue

        for p in pairs:
            chosen = by_id.get(p.chosen_id)
            rejected = by_id.get(p.rejected_id)
            if not chosen or not rejected:
                continue

            if p.rel == "tie":
                rank_gap = 0.0
            else:
                cg = group_index.get(p.chosen_id, 0)
                rg = group_index.get(p.rejected_id, cg)
                rank_gap = (rg - cg) / max(1, g_count - 1)

            cs = get_score(p.chosen_id)
            rs = get_score(p.rejected_id)
            score_gap = 0.0
            if cs is not None and rs is not None:
                score_gap = (float(cs) - float(rs)) / 4.0

            margin = rank_gap + score_gap

            records.append(
                {
                    "prompt": task.prompt,
                    "chosen": get_content(p.chosen_id),
                    "rejected": get_content(p.rejected_id),
                    "chosen_model": chosen.model_id,
                    "rejected_model": rejected.model_id,
                    "margin": margin,
                    "annotator": str(ann.annotator_id),
                    "export_job_id": export_job_id,
                    "rel": p.rel,
                }
            )

    return records


def _task_kappa_for_filter(db: Session, task_id: int) -> Optional[float]:
    anns = db.scalars(
        select(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
    ).all()
    labels_by_annotator: dict[int, list] = {}
    for a in anns:
        ranking: list[int] = json.loads(a.ranking)
        ranking_groups = _safe_json_loads(a.ranking_groups)
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        labels_by_annotator[a.annotator_id] = labels_from_groups(groups)
    return average_pairwise_kappa(labels_by_annotator)


def _encode_records(*, records: list[dict], payload: ExportRequest) -> tuple[str, str]:
    if payload.file_type == "jsonl":
        return "\\n".join(json.dumps(r, ensure_ascii=False) for r in records) + ("\\n" if records else ""), "application/jsonl"

    if payload.file_type == "json":
        return json.dumps(records, ensure_ascii=False), "application/json"

    if payload.file_type == "csv":
        buf = StringIO()
        if payload.format == "alpaca":
            fieldnames = ["instruction", "input", "output"]
        else:
            fieldnames = [
                "prompt",
                "chosen",
                "rejected",
                "chosen_model",
                "rejected_model",
                "margin",
                "annotator",
                "export_job_id",
                "rel",
            ]
        w = csv.DictWriter(buf, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in fieldnames})
        return buf.getvalue(), "text/csv"

    raise HTTPException(status_code=400, detail="unsupported file_type")


def _can_access_job(job: ExportJob, user) -> bool:
    if getattr(user, "role", None) == "admin":
        return True
    return job.created_by == getattr(user, "id", None)


@router.post("")
def export_data(payload: ExportRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    export_job_id = payload.export_job_id or str(uuid.uuid4())

    tasks_q = select(Task).order_by(Task.id.asc())
    if payload.exclude_dropped:
        tasks_q = tasks_q.where(Task.status != "dropped")
    tasks = db.scalars(tasks_q).all()

    records: list[dict] = []

    for task in tasks:
        if payload.min_kappa is not None:
            k = _task_kappa_for_filter(db, task.id)
            if k is not None and k < payload.min_kappa:
                continue

        anns = db.scalars(
            select(Annotation).where(Annotation.task_id == task.id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
        ).all()
        if not anns:
            continue

        responses = db.scalars(select(Response).where(Response.task_id == task.id)).all()
        records.extend(
            _build_records_for_task(
                task=task, annotations=anns, responses=responses, payload=payload, export_job_id=export_job_id
            )
        )

    content, media_type = _encode_records(records=records, payload=payload)

    job = ExportJob(
        id=export_job_id,
        created_by=_user.id,
        format=payload.format,
        file_type=payload.file_type,
        exclude_dropped=payload.exclude_dropped,
        min_kappa=payload.min_kappa,
        use_edits=payload.use_edits,
        tie_handling=payload.tie_handling,
        status="done",
        file_path=None,
    )

    if payload.inline:
        db.merge(job)
        db.commit()
        stored = db.get(ExportJob, export_job_id)
        if stored is None:
            raise HTTPException(status_code=500, detail="export job not persisted")
        if payload.file_type == "json":
            return JSONResponse(content=json.loads(content))
        return PlainTextResponse(content, media_type=media_type)

    ext = payload.file_type
    file_path = _export_dir() / f"{export_job_id}.{ext}"
    file_path.write_text(content, encoding="utf-8")
    job.file_path = str(file_path)
    db.merge(job)
    db.commit()
    stored = db.get(ExportJob, export_job_id)
    if stored is None:
        raise HTTPException(status_code=500, detail="export job not persisted")

    return ExportJobOut(
        id=stored.id,
        format=stored.format,
        file_type=stored.file_type,
        status=stored.status,
        created_at=stored.created_at,
        download_url=f"/api/export/jobs/{stored.id}/download",
    )


@router.get("/jobs/{job_id}", response_model=ExportJobOut)
def get_export_job(job_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    job = db.get(ExportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ExportJob not found")
    if not _can_access_job(job, _user):
        raise HTTPException(status_code=403, detail="Forbidden")
    return ExportJobOut(
        id=job.id,
        format=job.format,
        file_type=job.file_type,
        status=job.status,
        created_at=job.created_at,
        download_url=f"/api/export/jobs/{job.id}/download" if job.file_path else None,
    )


@router.get("/jobs", response_model=list[ExportJobOut])
def list_export_jobs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    limit = max(1, min(200, limit))
    offset = max(0, offset)

    q = select(ExportJob).order_by(ExportJob.created_at.desc()).limit(limit).offset(offset)
    if getattr(_user, "role", None) != "admin":
        q = q.where(ExportJob.created_by == _user.id)

    jobs = db.scalars(q).all()
    return [
        ExportJobOut(
            id=j.id,
            format=j.format,
            file_type=j.file_type,
            status=j.status,
            created_at=j.created_at,
            download_url=f"/api/export/jobs/{j.id}/download" if j.file_path else None,
        )
        for j in jobs
    ]


@router.delete("/jobs/{job_id}")
def delete_export_job(job_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    job = db.get(ExportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ExportJob not found")
    if not _can_access_job(job, _user):
        raise HTTPException(status_code=403, detail="Forbidden")

    if job.file_path:
        path = pathlib.Path(job.file_path)
        if path.exists():
            path.unlink()

    db.delete(job)
    db.commit()
    return {"ok": True}


@router.get("/jobs/{job_id}/download")
def download_export_job(job_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    job = db.get(ExportJob, job_id)
    if not job or not job.file_path:
        raise HTTPException(status_code=404, detail="ExportJob not found")
    if not _can_access_job(job, _user):
        raise HTTPException(status_code=403, detail="Forbidden")
    path = pathlib.Path(job.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")
