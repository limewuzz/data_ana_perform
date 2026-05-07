from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    format: Mapped[str] = mapped_column(String(32))
    file_type: Mapped[str] = mapped_column(String(16))
    exclude_dropped: Mapped[bool] = mapped_column(default=True)
    min_kappa: Mapped[Optional[float]] = mapped_column(nullable=True)
    use_edits: Mapped[bool] = mapped_column(default=True)
    tie_handling: Mapped[str] = mapped_column(String(16), default="random")
    status: Mapped[str] = mapped_column(String(16), default="done")
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
