def _register(client, email, role="annotator", name=None):
    payload = {"email": email, "password": "pass", "role": role}
    if name is not None:
        payload["name"] = name
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"authorization": f"Bearer {token}"}


def test_task_starts_pending_and_single_drop_marks_dropped(client):
    token1 = _register(client, "dropper@b.com")
    token2 = _register(client, "peer@b.com")

    task = client.post("/api/tasks", headers=_auth_headers(token1), json={"prompt": "hi", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    assert task.status_code == 200
    task_id = task.json()["id"]
    assert task.json()["status"] == "pending"

    claim = client.post(f"/api/queue/claim/{task_id}", headers=_auth_headers(token1))
    assert claim.status_code == 200

    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token1)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    dropped = client.post(
        "/api/annotations",
        headers=_auth_headers(token1),
        json={"task_id": task_id, "ranking_groups": [[r1, r2]], "is_dropped": True, "drop_reason": "bad"},
    )
    assert dropped.status_code == 200

    detail = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token1))
    assert detail.status_code == 200
    assert detail.json()["status"] == "dropped"

    nxt = client.post("/api/queue/next", headers=_auth_headers(token2), json={})
    assert nxt.status_code == 200
    assert nxt.json()["task"] is None


def test_task_import_and_task_list_enrichment(client):
    admin = _register(client, "admin-import@b.com", role="admin")

    imported = client.post(
        "/api/tasks/import",
        headers=_auth_headers(admin),
        json={
            "tasks": [
                {"prompt": "python function", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"], "category": "eng"},
                {"prompt": "math equation", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"], "category": "math"},
            ]
        },
    )
    assert imported.status_code == 200
    assert len(imported.json()["created"]) == 2

    listing = client.get("/api/tasks?limit=10&offset=0", headers=_auth_headers(admin))
    assert listing.status_code == 200
    assert len(listing.json()) == 2
    assert "response_count" in listing.json()[0]
    assert "annotation_count" in listing.json()[0]
    assert "kappa" in listing.json()[0]


def test_queue_progress_and_history(client):
    token = _register(client, "annotator-progress@b.com")

    task = client.post("/api/tasks", headers=_auth_headers(token), json={"prompt": "history", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id = task.json()["id"]
    claim = client.post(f"/api/queue/claim/{task_id}", headers=_auth_headers(token))
    assert claim.status_code == 200

    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    ann = client.post("/api/annotations", headers=_auth_headers(token), json={"task_id": task_id, "ranking": [r1, r2]})
    assert ann.status_code == 200

    progress = client.get("/api/queue/progress", headers=_auth_headers(token))
    assert progress.status_code == 200
    assert progress.json()["total_tasks"] >= 1
    assert progress.json()["annotated_tasks"] >= 1

    history = client.get("/api/queue/history?limit=10&offset=0", headers=_auth_headers(token))
    assert history.status_code == 200
    assert history.json()["items"][0]["task_id"] == task_id


def test_user_management_endpoints(client):
    admin = _register(client, "admin-users@b.com", role="admin", name="Admin")
    user = _register(client, "worker@b.com", role="annotator", name="Worker")

    me = client.get("/api/users/me", headers=_auth_headers(user))
    assert me.status_code == 200
    assert me.json()["name"] == "Worker"

    forbidden = client.get("/api/users", headers=_auth_headers(user))
    assert forbidden.status_code == 403

    listing = client.get("/api/users", headers=_auth_headers(admin))
    assert listing.status_code == 200
    assert len(listing.json()) == 2
    worker = next(item for item in listing.json() if item["email"] == "worker@b.com")

    updated = client.patch(
        f"/api/users/{worker['id']}",
        headers=_auth_headers(admin),
        json={"role": "reviewer", "name": "Reviewer Worker"},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "reviewer"
    assert updated.json()["name"] == "Reviewer Worker"
