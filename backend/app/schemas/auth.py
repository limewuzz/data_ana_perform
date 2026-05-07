from typing import Optional

from app.schemas.base import AppBaseModel


class Token(AppBaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(AppBaseModel):
    email: str
    password: str


class RegisterRequest(AppBaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: str = "annotator"
