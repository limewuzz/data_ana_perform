from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.schemas.base import AppBaseModel


class ExportJobOut(AppBaseModel):
    id: str
    format: str
    file_type: str
    status: str
    created_at: datetime
    download_url: Optional[str] = None

