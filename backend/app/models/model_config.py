from __future__ import annotations

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(default=True)
    base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    api_key_env: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    params_json: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
