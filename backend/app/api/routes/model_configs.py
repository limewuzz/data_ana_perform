from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.model_config import ModelConfig
from app.schemas.model_config import ModelConfigCreate, ModelConfigOut, ModelConfigUpdate

router = APIRouter(prefix="/api/model-configs", tags=["model-configs"])


def _out(m: ModelConfig) -> ModelConfigOut:
    params = None
    if m.params_json:
        params = json.loads(m.params_json)
    return ModelConfigOut(
        id=m.id,
        model_id=m.model_id,
        name=m.name,
        provider=m.provider,
        enabled=m.enabled,
        base_url=m.base_url,
        api_key_env=m.api_key_env,
        system_prompt=m.system_prompt,
        params=params,
    )


@router.get("", response_model=list[ModelConfigOut])
def list_model_configs(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    models = db.scalars(select(ModelConfig).order_by(ModelConfig.id.asc())).all()
    return [_out(m) for m in models]


@router.post("", response_model=ModelConfigOut)
def create_model_config(payload: ModelConfigCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    existing = db.scalar(select(ModelConfig).where(ModelConfig.model_id == payload.model_id))
    if existing:
        raise HTTPException(status_code=409, detail="model_id already exists")
    m = ModelConfig(
        model_id=payload.model_id,
        name=payload.name,
        provider=payload.provider,
        enabled=payload.enabled,
        base_url=payload.base_url,
        api_key_env=payload.api_key_env,
        system_prompt=payload.system_prompt,
        params_json=json.dumps(payload.params) if payload.params is not None else None,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.patch("/{model_config_id}", response_model=ModelConfigOut)
def update_model_config(
    model_config_id: int,
    payload: ModelConfigUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    m = db.get(ModelConfig, model_config_id)
    if not m:
        raise HTTPException(status_code=404, detail="ModelConfig not found")

    data = payload.model_dump(exclude_unset=True)
    if "params" in data:
        m.params_json = json.dumps(data.pop("params")) if data.get("params") is not None else None
    for k, v in data.items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.delete("/{model_config_id}")
def delete_model_config(model_config_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    m = db.get(ModelConfig, model_config_id)
    if not m:
        raise HTTPException(status_code=404, detail="ModelConfig not found")
    db.delete(m)
    db.commit()
    return {"ok": True}
