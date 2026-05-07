def _register(client, email, role):
    r = client.post("/auth/register", json={"email": email, "password": "pass", "role": role})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"authorization": f"Bearer {token}"}


def test_review_sets_requires_reviewer(client):
    token = _register(client, "u@b.com", "annotator")
    r = client.get("/api/review-sets/low-kappa", headers=_auth_headers(token))
    assert r.status_code == 403


def test_low_kappa_and_action(client):
    reviewer = _register(client, "r@b.com", "reviewer")
    a1 = _register(client, "a1@b.com", "annotator")
    a2 = _register(client, "a2@b.com", "annotator")

    t = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "p", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    assert t.status_code == 200
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(a1)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]

    r = client.post("/api/annotations", headers=_auth_headers(a1), json={"task_id": task_id, "ranking": [r1, r2]})
    assert r.status_code == 200
    r = client.post("/api/annotations", headers=_auth_headers(a2), json={"task_id": task_id, "ranking": [r2, r1]})
    assert r.status_code == 200

    lk = client.get("/api/review-sets/low-kappa?threshold=0.9", headers=_auth_headers(reviewer))
    assert lk.status_code == 200
    items = lk.json()["items"]
    assert any(it["task_id"] == task_id for it in items)

    act = client.post(
        f"/api/review-sets/tasks/{task_id}/action",
        headers=_auth_headers(reviewer),
        json={"action": "needs_rework"},
    )
    assert act.status_code == 200
    assert act.json()["review_status"] == "needs_rework"

    nr = client.get("/api/review-sets/needs-rework", headers=_auth_headers(reviewer))
    assert nr.status_code == 200
    assert any(it["task_id"] == task_id for it in nr.json()["items"])

    ev = client.get(f"/api/review-sets/events?task_id={task_id}", headers=_auth_headers(reviewer))
    assert ev.status_code == 200
    assert any(e["task_id"] == task_id for e in ev.json())


def test_drop_reason_stats(client):
    reviewer = _register(client, "r2@b.com", "reviewer")
    a1 = _register(client, "a3@b.com", "annotator")

    t = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "drop", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(a1)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    r = client.post(
        "/api/annotations",
        headers=_auth_headers(a1),
        json={"task_id": task_id, "ranking": [r1, r2], "is_dropped": True, "drop_reason": "bad"},
    )
    assert r.status_code == 200

    stats = client.get("/api/review-sets/drop-reasons", headers=_auth_headers(reviewer))
    assert stats.status_code == 200
    assert stats.json()["counts"].get("bad", 0) >= 1


def test_annotator_anomalies_set(client):
    reviewer = _register(client, "rr@b.com", "reviewer")
    a1 = _register(client, "aa1@b.com", "annotator")
    a2 = _register(client, "aa2@b.com", "annotator")

    t = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "p", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(a1)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    r = client.post("/api/annotations", headers=_auth_headers(a1), json={"task_id": task_id, "ranking": [r1, r2], "duration_ms": 1000})
    assert r.status_code == 200
    r = client.post("/api/annotations", headers=_auth_headers(a2), json={"task_id": task_id, "ranking": [r2, r1], "duration_ms": 2000})
    assert r.status_code == 200

    t2 = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "drop", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id2 = t2.json()["id"]
    rs2 = client.get(f"/api/tasks/{task_id2}", headers=_auth_headers(a1)).json()["responses"]
    x1, x2 = rs2[0]["id"], rs2[1]["id"]
    r = client.post(
        "/api/annotations",
        headers=_auth_headers(a1),
        json={"task_id": task_id2, "ranking": [x1, x2], "is_dropped": True, "drop_reason": "bad", "duration_ms": 9999},
    )
    assert r.status_code == 200

    s = client.get("/api/review-sets/annotators/anomalies?drop_rate_gte=0.5&include_all=false", headers=_auth_headers(reviewer))
    assert s.status_code == 200
    items = s.json()["items"]
    assert any(it["annotator_id"] > 0 for it in items)


def test_low_margin_and_slow_and_inconsistencies_sets(client):
    reviewer = _register(client, "rrr@b.com", "reviewer")
    a1 = _register(client, "bb1@b.com", "annotator")

    t = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "tie", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(a1)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    r = client.post(
        "/api/annotations",
        headers=_auth_headers(a1),
        json={"task_id": task_id, "ranking_groups": [[r1, r2]], "duration_ms": 20000},
    )
    assert r.status_code == 200

    lm = client.get("/api/review-sets/low-margin?threshold=0.1&ratio_gte=0.5", headers=_auth_headers(reviewer))
    assert lm.status_code == 200
    assert any(it["task_id"] == task_id for it in lm.json()["items"])

    slow = client.get("/api/review-sets/slow-tasks?avg_duration_ms_gte=10000", headers=_auth_headers(reviewer))
    assert slow.status_code == 200
    assert any(it["task_id"] == task_id for it in slow.json()["items"])

    t2 = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "flip1", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id2 = t2.json()["id"]
    rs2 = client.get(f"/api/tasks/{task_id2}", headers=_auth_headers(a1)).json()["responses"]
    m1_id = next(x["id"] for x in rs2 if x["model_id"] == "kimi-k2.6")
    m2_id = next(x["id"] for x in rs2 if x["model_id"] == "mimo-v2.5-pro")
    r = client.post("/api/annotations", headers=_auth_headers(a1), json={"task_id": task_id2, "ranking": [m2_id, m1_id]})
    assert r.status_code == 200

    t3 = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "flip2", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id3 = t3.json()["id"]
    rs3 = client.get(f"/api/tasks/{task_id3}", headers=_auth_headers(a1)).json()["responses"]
    m1_id3 = next(x["id"] for x in rs3 if x["model_id"] == "kimi-k2.6")
    m2_id3 = next(x["id"] for x in rs3 if x["model_id"] == "mimo-v2.5-pro")
    r = client.post("/api/annotations", headers=_auth_headers(a1), json={"task_id": task_id3, "ranking": [m1_id3, m2_id3]})
    assert r.status_code == 200

    inc = client.get("/api/review-sets/annotators/inconsistencies?min_conflict_pairs=1", headers=_auth_headers(reviewer))
    assert inc.status_code == 200
    assert any(it["annotator_id"] > 0 for it in inc.json()["items"])


def test_bulk_review_action_writes_events(client):
    reviewer = _register(client, "bulk@b.com", "reviewer")
    a1 = _register(client, "bulk-a@b.com", "annotator")

    t1 = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "b1", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    t2 = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "b2", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    assert t1.status_code == 200 and t2.status_code == 200
    id1 = t1.json()["id"]
    id2 = t2.json()["id"]

    r = client.post(
        "/api/review-sets/bulk-action",
        headers=_auth_headers(reviewer),
        json={"task_ids": [id1, id2], "action": "locked", "reason": "batch", "source_set": "low-margin"},
    )
    assert r.status_code == 200
    assert r.json()["updated"] == 2

    ev = client.get("/api/review-sets/events?limit=50", headers=_auth_headers(reviewer))
    assert ev.status_code == 200
    got = [(e["task_id"], e["action"]) for e in ev.json()]
    assert (id1, "locked") in got or (id2, "locked") in got


def test_apply_set_action(client):
    reviewer = _register(client, "apply@b.com", "reviewer")
    a1 = _register(client, "apply-a@b.com", "annotator")
    a2 = _register(client, "apply-b@b.com", "annotator")

    t = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "lk", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(a1)).json()["responses"]
    m1_id = next(x["id"] for x in rs if x["model_id"] == "kimi-k2.6")
    m2_id = next(x["id"] for x in rs if x["model_id"] == "mimo-v2.5-pro")
    r = client.post("/api/annotations", headers=_auth_headers(a1), json={"task_id": task_id, "ranking": [m1_id, m2_id], "duration_ms": 20000})
    assert r.status_code == 200
    r = client.post("/api/annotations", headers=_auth_headers(a2), json={"task_id": task_id, "ranking": [m2_id, m1_id], "duration_ms": 20000})
    assert r.status_code == 200

    a = client.post(
        "/api/review-sets/apply-set-action",
        headers=_auth_headers(reviewer),
        json={"set_name": "low-kappa", "action": "needs_rework", "reason": "auto", "params": {"threshold": 0.9}},
    )
    assert a.status_code == 200
    assert a.json()["updated"] >= 1

    ev = client.get(f"/api/review-sets/events?task_id={task_id}", headers=_auth_headers(reviewer))
    assert ev.status_code == 200
    assert any(e["source_set"] == "low-kappa" for e in ev.json())


def test_apply_set_action_dry_run(client):
    reviewer = _register(client, "apply2@b.com", "reviewer")
    a1 = _register(client, "apply2-a@b.com", "annotator")
    a2 = _register(client, "apply2-b@b.com", "annotator")

    t = client.post("/api/tasks", headers=_auth_headers(a1), json={"prompt": "lk", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(a1)).json()["responses"]
    m1_id = next(x["id"] for x in rs if x["model_id"] == "kimi-k2.6")
    m2_id = next(x["id"] for x in rs if x["model_id"] == "mimo-v2.5-pro")
    r = client.post("/api/annotations", headers=_auth_headers(a1), json={"task_id": task_id, "ranking": [m1_id, m2_id]})
    assert r.status_code == 200
    r = client.post("/api/annotations", headers=_auth_headers(a2), json={"task_id": task_id, "ranking": [m2_id, m1_id]})
    assert r.status_code == 200

    a = client.post(
        "/api/review-sets/apply-set-action",
        headers=_auth_headers(reviewer),
        json={"set_name": "low-kappa", "action": "needs_rework", "dry_run": True, "params": {"threshold": 0.9}},
    )
    assert a.status_code == 200
    assert a.json()["dry_run"] is True
    assert task_id in a.json()["task_ids"]

    ev = client.get(f"/api/review-sets/events?task_id={task_id}", headers=_auth_headers(reviewer))
    assert ev.status_code == 200
    assert len(ev.json()) == 0
