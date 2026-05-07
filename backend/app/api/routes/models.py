from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.schemas.task import ModelInfo
from app.services.model_registry import get_available_models

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[ModelInfo])
def list_models(_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_available_models(db)
