from __future__ import annotations

from typing import Optional

from app.schemas.base import AppBaseModel


class ExportRequest(AppBaseModel):
    format: str = "dpo"
    file_type: str = "jsonl"
    exclude_dropped: bool = True
    min_kappa: Optional[float] = 0.4
    use_edits: bool = True

    tie_handling: str = "random"
    export_job_id: Optional[str] = None
    tie_seed: Optional[str] = None
    inline: bool = False
