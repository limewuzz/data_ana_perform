from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24
    target_annotations_per_task: int = 2
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None
    xiaomimimo_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    xiaomimimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    openai_max_tokens: int = 1024
    anthropic_max_tokens: int = 1024
    kimi_max_tokens: int = 1024
    xiaomimimo_max_tokens: int = 1024
    openai_temperature: float = 0.7
    kimi_temperature: float = 1.0
    xiaomimimo_temperature: float = 0.7


settings = Settings()
