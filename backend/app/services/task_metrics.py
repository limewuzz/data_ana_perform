from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.annotation import Annotation
from app.models.response import Response
from app.models.task import Task
from app.services.kappa import average_pairwise_kappa, labels_from_groups
from app.services.pairwise import to_groups

LOW_KAPPA_THRESHOLD = 0.4
LOW_DISTINCTNESS_THRESHOLD = 0.85


def _load_json(value: str | None):
    return json.loads(value) if value else None


def infer_category(prompt: str, category: str | None = None) -> str:
    if category:
        return category

    text = prompt.lower()
    rules = [
        ("code", ("python", "java", "javascript", "typescript", "code", "bug", "function", "sql")),
        ("math", ("math", "equation", "algebra", "geometry", "calculate", "prove")),
        ("writing", ("essay", "rewrite", "summarize", "summary", "draft", "blog", "translate")),
        ("reasoning", ("why", "explain", "reason", "analyze", "compare")),
    ]
    for name, keywords in rules:
        if any(k in text for k in keywords):
            return name
    return "uncategorized"


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9\u4e00-\u9fff]+", text.lower()))


def jaccard_similarity(text1: str, text2: str) -> float:
    left = _tokenize(text1)
    right = _tokenize(text2)
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def task_kappa(db: Session, task_id: int) -> Optional[float]:
    anns = db.scalars(
        select(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
    ).all()
    labels_by_annotator: dict[int, list] = {}
    for ann in anns:
        ranking = json.loads(ann.ranking)
        ranking_groups = _load_json(ann.ranking_groups)
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        labels_by_annotator[ann.annotator_id] = labels_from_groups(groups)
    return average_pairwise_kappa(labels_by_annotator)


def category_kappas(db: Session) -> list[dict]:
    tasks = db.scalars(select(Task).order_by(Task.id.asc())).all()
    grouped: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    counts = Counter()

    for task in tasks:
        category = infer_category(task.prompt, task.category)
        counts[category] += 1
        anns = db.scalars(
            select(Annotation).where(Annotation.task_id == task.id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
        ).all()
        for ann in anns:
            ranking = json.loads(ann.ranking)
            ranking_groups = _load_json(ann.ranking_groups)
            groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
            grouped[category][ann.annotator_id].extend(labels_from_groups(groups))

    items = []
    for category, labels_by_annotator in sorted(grouped.items()):
        items.append(
            {
                "category": category,
                "task_count": counts.get(category, 0),
                "kappa": average_pairwise_kappa(labels_by_annotator),
            }
        )
    for category, count in sorted(counts.items()):
        if any(item["category"] == category for item in items):
            continue
        items.append({"category": category, "task_count": count, "kappa": None})
    items.sort(key=lambda item: item["category"])
    return items


def category_distribution(tasks: Iterable[Task]) -> list[dict]:
    counts = Counter(infer_category(task.prompt, task.category) for task in tasks)
    return [{"category": name, "task_count": count} for name, count in sorted(counts.items())]


def task_distinctness(db: Session, task_id: int) -> Optional[float]:
    responses = db.scalars(select(Response).where(Response.task_id == task_id).order_by(Response.id.asc())).all()
    by_id = {response.id: response for response in responses}
    anns = db.scalars(
        select(Annotation).where(Annotation.task_id == task_id, Annotation.is_dropped == False).order_by(Annotation.id.asc())
    ).all()
    similarities: list[float] = []
    for ann in anns:
        ranking = json.loads(ann.ranking)
        ranking_groups = _load_json(ann.ranking_groups)
        edits = _load_json(ann.edits) or {}
        groups = to_groups(ranking=ranking, ranking_groups=ranking_groups)
        if not groups or not groups[0] or not groups[-1]:
            continue
        top_id = groups[0][0]
        bottom_id = groups[-1][-1]
        top = edits.get(str(top_id), edits.get(top_id, by_id.get(top_id).content if by_id.get(top_id) else ""))
        bottom = edits.get(str(bottom_id), edits.get(bottom_id, by_id.get(bottom_id).content if by_id.get(bottom_id) else ""))
        similarities.append(jaccard_similarity(top, bottom))
    if not similarities:
        return None
    return sum(similarities) / len(similarities)


def task_is_usable(db: Session, task: Task) -> bool:
    if task.status == "dropped":
        return False
    kappa = task_kappa(db, task.id)
    if kappa is None or kappa < LOW_KAPPA_THRESHOLD:
        return False
    distinctness = task_distinctness(db, task.id)
    if distinctness is not None and distinctness > LOW_DISTINCTNESS_THRESHOLD:
        return False
    return True


def initial_first_response_id(db: Session, task_id: int) -> int | None:
    response = db.scalars(select(Response).where(Response.task_id == task_id).order_by(Response.id.asc())).first()
    return response.id if response else None
