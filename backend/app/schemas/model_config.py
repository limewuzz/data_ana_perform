from __future__ import annotations

from typing import Any, Dict, Optional

from app.schemas.base import AppBaseModel


class ModelConfigOut(AppBaseModel):
    id: int
    model_id: str
    name: str
    provider: str
    enabled: bool
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    system_prompt: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class ModelConfigCreate(AppBaseModel):
    model_id: str
    name: str
    provider: str
    enabled: bool = True
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    system_prompt: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class ModelConfigUpdate(AppBaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    system_prompt: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
