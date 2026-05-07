def _register(client, email, role):
    r = client.post("/auth/register", json={"email": email, "password": "pass", "role": role})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"authorization": f"Bearer {token}"}


def _create_task(client, token, prompt="p"):
    r = client.post("/api/tasks", headers=_auth_headers(token), json={"prompt": prompt, "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    assert r.status_code == 200
    task_id = r.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token)).json()["responses"]
    return task_id, rs[0]["id"], rs[1]["id"]


def test_stats_endpoints(client):
    a1 = _register(client, "a1@b.com", "annotator")
    a2 = _register(client, "a2@b.com", "annotator")

    task_id, r1, r2 = _create_task(client, a1, prompt="python bug fix")

    r = client.post(
        "/api/annotations",
        headers=_auth_headers(a1),
        json={
            "task_id": task_id,
            "ranking": [r1, r2],
            "duration_ms": 1000,
            "edits": {str(r1): "same answer", str(r2): "same answer"},
        },
    )
    assert r.status_code == 200

    r = client.post(
        "/api/annotations",
        headers=_auth_headers(a2),
        json={
            "task_id": task_id,
            "ranking": [r1, r2],
            "duration_ms": 2000,
            "edits": {str(r1): "same answer", str(r2): "same answer"},
        },
    )
    assert r.status_code == 200

    k = client.get("/api/stats/kappa", headers=_auth_headers(a1))
    assert k.status_code == 200
    obj = k.json()
    assert "global_kappa" in obj
    assert len(obj["per_task"]) >= 1
    assert len(obj["per_category"]) >= 1
    assert obj["per_category"][0]["category"] == "code"

    d = client.get("/api/stats/dashboard", headers=_auth_headers(a1))
    assert d.status_code == 200
    dobj = d.json()
    assert dobj["overview"]["total_tasks"] >= 1
    assert len(dobj["kappa_histogram"]) == 10
    assert "usable_data_ratio" in dobj["overview"]
    assert "low_distinctness_ratio" in dobj["overview"]
    assert len(dobj["category_distribution"]) >= 1
    assert len(dobj["similarity_histogram"]) == 10
    assert any(item["task_id"] == task_id for item in dobj["low_distinctness_tasks"])

    s = client.get("/api/stats/annotators", headers=_auth_headers(a1))
    assert s.status_code == 200
    sobj = s.json()
    assert len(sobj["items"]) >= 1
    assert "position_bias" in sobj["items"][0]
