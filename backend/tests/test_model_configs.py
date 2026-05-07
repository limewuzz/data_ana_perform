def _register(client, email, role):
    r = client.post("/auth/register", json={"email": email, "password": "pass", "role": role})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"authorization": f"Bearer {token}"}


def test_model_configs_requires_admin(client):
    token = _register(client, "u@b.com", "annotator")
    r = client.get("/api/model-configs", headers=_auth_headers(token))
    assert r.status_code == 403


def test_model_configs_crud(client):
    token = _register(client, "admin@b.com", "admin")

    r = client.post(
        "/api/model-configs",
        headers=_auth_headers(token),
        json={"model_id": "http1", "name": "HTTP Model", "provider": "http", "enabled": False, "base_url": "http://x"},
    )
    assert r.status_code == 200
    mid = r.json()["id"]

    r2 = client.get("/api/model-configs", headers=_auth_headers(token))
    assert r2.status_code == 200
    ids = {m["model_id"] for m in r2.json()}
    assert "kimi-k2.6" in ids
    assert "mimo-v2.5-pro" in ids
    assert "http1" in ids

    r3 = client.patch("/api/model-configs/%d" % mid, headers=_auth_headers(token), json={"enabled": True})
    assert r3.status_code == 200
    assert r3.json()["enabled"] is True

    r4 = client.delete("/api/model-configs/%d" % mid, headers=_auth_headers(token))
    assert r4.status_code == 200
    assert r4.json()["ok"] is True
