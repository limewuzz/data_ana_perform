from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.api.router import api_router
from app.core.db import Base, SessionLocal, engine
from app import models


def _sync_default_models(db) -> None:
    from app.models.model_config import ModelConfig

    desired = {
        "kimi-k2.6": {
            "name": "Kimi K2.6",
            "provider": "kimi",
            "enabled": True,
            "base_url": None,
            "api_key_env": None,
            "system_prompt": None,
            "params_json": None,
        },
        "mimo-v2.5-pro": {
            "name": "Mimo v2.5 Pro",
            "provider": "xiaomimimo",
            "enabled": True,
            "base_url": None,
            "api_key_env": None,
            "system_prompt": None,
            "params_json": None,
        },
    }

    existing = {model.model_id: model for model in db.scalars(select(ModelConfig)).all()}
    for model_id, payload in desired.items():
        model = existing.get(model_id)
        if model is None:
            db.add(ModelConfig(model_id=model_id, **payload))
            continue
        for key, value in payload.items():
            setattr(model, key, value)

    for model_id, model in existing.items():
        if model_id not in desired:
            db.delete(model)

    db.commit()


def _initialize_app() -> None:
    Base.metadata.create_all(bind=engine)
    if str(engine.url).startswith("sqlite"):
        with engine.connect() as conn:
            tasks_cols = conn.execute(text("PRAGMA table_info(tasks)")).fetchall()
            tasks_col_names = {c[1] for c in tasks_cols}
            if "review_status" not in tasks_col_names:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN review_status VARCHAR(32) NOT NULL DEFAULT 'none'"))
                conn.commit()

            mc_cols = conn.execute(text("PRAGMA table_info(model_configs)")).fetchall()
            mc_col_names = {c[1] for c in mc_cols}
            if "system_prompt" not in mc_col_names:
                conn.execute(text("ALTER TABLE model_configs ADD COLUMN system_prompt VARCHAR(2048)"))
                conn.commit()
            if "params_json" not in mc_col_names:
                conn.execute(text("ALTER TABLE model_configs ADD COLUMN params_json VARCHAR(2048)"))
                conn.commit()

            user_cols = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            user_col_names = {c[1] for c in user_cols}
            if "name" not in user_col_names:
                conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(255)"))
                conn.commit()
            if "created_at" not in user_col_names:
                conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME"))
                conn.commit()
    db = SessionLocal()
    try:
        _sync_default_models(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _initialize_app()
    yield


app = FastAPI(title="Preference Data Annotation Workbench API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173",
        "http://127.0.0.1:4174",
        "http://127.0.0.1:4175",
        "http://localhost:4173",
        "http://localhost:4174",
        "http://localhost:4175",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


app.include_router(api_router)
