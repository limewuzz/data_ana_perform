from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.schemas.base import AppBaseModel


class UserOut(AppBaseModel):
    id: int
    email: str
    name: Optional[str] = None
    role: str
    created_at: Optional[datetime] = None


class UserUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
