from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.user import UserOut, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role, created_at=user.created_at)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return _out(user)


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _user=Depends(require_admin)):
    users = db.scalars(select(User).order_by(User.id.asc())).all()
    return [_out(user) for user in users]


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdateRequest, db: Session = Depends(get_db), _user=Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.name is not None:
        user.name = payload.name
    if payload.role is not None:
        user.role = payload.role
    db.commit()
    db.refresh(user)
    return _out(user)
