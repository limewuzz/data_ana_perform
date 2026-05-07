def _register(client, email="a@b.com", password="pass"):
    r = client.post("/auth/register", json={"email": email, "password": password, "role": "annotator"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"authorization": f"Bearer {token}"}


def test_models_requires_auth(client):
    r = client.get("/api/models")
    assert r.status_code == 401


def test_register_login_and_models(client):
    token = _register(client)
    r = client.get("/api/models", headers=_auth_headers(token))
    assert r.status_code == 200
    models = r.json()
    assert isinstance(models, list)
    ids = {m["id"] for m in models}
    assert "kimi-k2.6" in ids
    assert "mimo-v2.5-pro" in ids

    r2 = client.post("/auth/login", json={"email": "a@b.com", "password": "pass"})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_create_task_requires_two_models(client):
    token = _register(client)
    r = client.post("/api/tasks", headers=_auth_headers(token), json={"prompt": "hi", "model_ids": ["kimi-k2.6"]})
    assert r.status_code == 400


def test_create_task_unknown_model_rejected(client):
    token = _register(client)
    r = client.post("/api/tasks", headers=_auth_headers(token), json={"prompt": "hi", "model_ids": ["kimi-k2.6", "unknown"]})
    assert r.status_code == 400


def test_task_annotation_and_export(client):
    token = _register(client)

    r = client.post(
        "/api/tasks",
        headers=_auth_headers(token),
        json={"prompt": "p1", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"], "category": "c"},
    )
    assert r.status_code == 200
    task = r.json()
    task_id = task["id"]

    r2 = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token))
    assert r2.status_code == 200
    responses = r2.json()["responses"]
    assert len(responses) == 2
    assert any(x["content"].startswith("[test:kimi-k2.6]") or x["content"].startswith("[test:mimo-v2.5-pro]") for x in responses)
    r1, r2_ = responses[0]["id"], responses[1]["id"]

    r3 = client.post(
        "/api/annotations",
        headers=_auth_headers(token),
        json={
            "task_id": task_id,
            "ranking_groups": [[r1, r2_]],
            "scores": {str(r1): 5, str(r2_): 3},
            "duration_ms": 1234,
        },
    )
    assert r3.status_code == 200

    r4 = client.post(
        "/api/export",
        headers=_auth_headers(token),
        json={"format": "dpo", "tie_handling": "random", "inline": True},
    )
    assert r4.status_code == 200
    lines = [ln for ln in r4.text.splitlines() if ln.strip()]
    assert len(lines) >= 1


def test_drop_excluded_from_export(client):
    token = _register(client)
    r = client.post("/api/tasks", headers=_auth_headers(token), json={"prompt": "dropme", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    assert r.status_code == 200
    task_id = r.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]

    r2 = client.post(
        "/api/annotations",
        headers=_auth_headers(token),
        json={"task_id": task_id, "ranking_groups": [[r1, r2]], "is_dropped": True, "drop_reason": "bad"},
    )
    assert r2.status_code == 200

    out = client.post(
        "/api/export",
        headers=_auth_headers(token),
        json={"format": "dpo", "exclude_dropped": True, "inline": True},
    )
    assert out.status_code == 200
    assert "dropme" not in out.text
