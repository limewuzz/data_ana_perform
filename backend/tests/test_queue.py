def _register(client, email, role="annotator"):
    r = client.post("/auth/register", json={"email": email, "password": "pass", "role": role})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"authorization": f"Bearer {token}"}


def test_queue_next_and_claim_complete(client):
    u1 = _register(client, "u1@b.com")
    u2 = _register(client, "u2@b.com")

    t = client.post("/api/tasks", headers=_auth_headers(u1), json={"prompt": "q", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    assert t.status_code == 200
    task_id = t.json()["id"]

    n1 = client.post("/api/queue/next", headers=_auth_headers(u1), json={})
    assert n1.status_code == 200
    assert n1.json()["task"]["id"] == task_id

    c1 = client.post(f"/api/queue/claim/{task_id}", headers=_auth_headers(u1))
    assert c1.status_code == 200

    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(u1)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    a = client.post("/api/annotations", headers=_auth_headers(u1), json={"task_id": task_id, "ranking": [r1, r2]})
    assert a.status_code == 200

    n1b = client.post("/api/queue/next", headers=_auth_headers(u1), json={})
    assert n1b.status_code == 200
    assert n1b.json()["task"] is None

    n2 = client.post("/api/queue/next", headers=_auth_headers(u2), json={})
    assert n2.status_code == 200
    assert n2.json()["task"]["id"] == task_id

    done = client.post(f"/api/queue/complete/{task_id}", headers=_auth_headers(u1))
    assert done.status_code == 200
    assert done.json()["status"] in ("annotating", "completed", "dropped")


def test_queue_next_prefers_needs_rework_and_category_filter(client):
    u1 = _register(client, "u3@b.com")

    t1 = client.post(
        "/api/tasks",
        headers=_auth_headers(u1),
        json={"prompt": "a", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"], "category": "c1"},
    )
    t2 = client.post(
        "/api/tasks",
        headers=_auth_headers(u1),
        json={"prompt": "b", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"], "category": "c2"},
    )
    assert t1.status_code == 200 and t2.status_code == 200
    task1 = t1.json()["id"]
    task2 = t2.json()["id"]

    from app.core.db import SessionLocal
    from app.models.task import Task

    db = SessionLocal()
    try:
        obj = db.get(Task, task2)
        obj.review_status = "needs_rework"
        db.commit()
    finally:
        db.close()

    n = client.post("/api/queue/next", headers=_auth_headers(u1), json={"category": "c2"})
    assert n.status_code == 200
    assert n.json()["task"]["id"] == task2

    n2 = client.post("/api/queue/next", headers=_auth_headers(u1), json={"category": "c1"})
    assert n2.status_code == 200
    assert n2.json()["task"]["id"] == task1
