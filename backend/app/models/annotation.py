from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ranking: Mapped[str] = mapped_column(String)
    ranking_groups: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scores: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    edits: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_dropped: Mapped[bool] = mapped_column(Boolean, default=False)
    drop_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
