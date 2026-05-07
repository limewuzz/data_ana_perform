from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig
from app.schemas.task import ModelInfo


def get_available_models(db: Session) -> list[ModelInfo]:
    models = db.scalars(select(ModelConfig).where(ModelConfig.enabled == True).order_by(ModelConfig.id.asc())).all()
    return [ModelInfo(id=m.model_id, name=m.name, provider=m.provider, enabled=m.enabled) for m in models]
