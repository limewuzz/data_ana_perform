import os
import pathlib
import sys

import pytest

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session", autouse=True)
def _test_env(tmp_path_factory):
    os.environ.setdefault("APP_JWT_SECRET", "test-secret")
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["APP_DATABASE_URL"] = f"sqlite:///{db_path}"
    yield


@pytest.fixture()
def client(monkeypatch):
    from fastapi.testclient import TestClient

    from app.core.db import Base, engine
    from app.main import app

    async def _fake_call_model(*, model, prompt: str) -> str:
        return f"[test:{model.model_id}] {prompt}"

    monkeypatch.setattr("app.api.routes.tasks.call_model", _fake_call_model)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c
