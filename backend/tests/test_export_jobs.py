def _register(client, email="a@b.com", password="pass"):
    r = client.post("/auth/register", json={"email": email, "password": password, "role": "annotator"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"authorization": f"Bearer {token}"}


def test_export_job_download_flow(client):
    token = _register(client)
    t = client.post("/api/tasks", headers=_auth_headers(token), json={"prompt": "hi", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    assert t.status_code == 200
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    a = client.post("/api/annotations", headers=_auth_headers(token), json={"task_id": task_id, "ranking": [r1, r2]})
    assert a.status_code == 200

    job = client.post("/api/export", headers=_auth_headers(token), json={"format": "dpo", "file_type": "jsonl"})
    assert job.status_code == 200
    job_id = job.json()["id"]

    meta = client.get(f"/api/export/jobs/{job_id}", headers=_auth_headers(token))
    assert meta.status_code == 200
    assert meta.json()["download_url"].endswith("/download")

    dl = client.get(f"/api/export/jobs/{job_id}/download", headers=_auth_headers(token))
    assert dl.status_code == 200
    assert len(dl.content) > 0

    lst = client.get("/api/export/jobs?limit=10&offset=0", headers=_auth_headers(token))
    assert lst.status_code == 200
    ids = {j["id"] for j in lst.json()}
    assert job_id in ids

    d = client.delete(f"/api/export/jobs/{job_id}", headers=_auth_headers(token))
    assert d.status_code == 200
    assert d.json()["ok"] is True

    meta2 = client.get(f"/api/export/jobs/{job_id}", headers=_auth_headers(token))
    assert meta2.status_code == 404


def test_export_job_forbidden_between_users(client):
    token1 = _register(client, "u1@b.com")
    token2 = _register(client, "u2@b.com")

    t = client.post("/api/tasks", headers=_auth_headers(token1), json={"prompt": "hi2", "model_ids": ["kimi-k2.6", "mimo-v2.5-pro"]})
    task_id = t.json()["id"]
    rs = client.get(f"/api/tasks/{task_id}", headers=_auth_headers(token1)).json()["responses"]
    r1, r2 = rs[0]["id"], rs[1]["id"]
    a = client.post("/api/annotations", headers=_auth_headers(token1), json={"task_id": task_id, "ranking": [r1, r2]})
    assert a.status_code == 200

    job = client.post("/api/export", headers=_auth_headers(token1), json={"format": "dpo", "file_type": "jsonl"})
    job_id = job.json()["id"]

    meta = client.get(f"/api/export/jobs/{job_id}", headers=_auth_headers(token2))
    assert meta.status_code == 403
    dl = client.get(f"/api/export/jobs/{job_id}/download", headers=_auth_headers(token2))
    assert dl.status_code == 403
    d = client.delete(f"/api/export/jobs/{job_id}", headers=_auth_headers(token2))
    assert d.status_code == 403
