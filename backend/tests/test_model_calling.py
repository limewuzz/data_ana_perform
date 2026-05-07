import asyncio


def test_call_model_openai_missing_key_raises():
    from app.models.model_config import ModelConfig
    from app.services.model_calling import call_model

    m = ModelConfig(model_id="gpt-4o-mini", name="x", provider="openai", enabled=True, system_prompt="sys", params_json='{"max_tokens":123}')
    try:
        asyncio.run(call_model(model=m, prompt="hi"))
        assert False
    except ValueError as e:
        assert "missing api key" in str(e)


def test_call_model_kimi_missing_key_raises(monkeypatch):
    from app.core.config import settings
    from app.models.model_config import ModelConfig
    from app.services.model_calling import call_model

    monkeypatch.setattr(settings, "kimi_api_key", None)
    m = ModelConfig(model_id="kimi-k2.6", name="x", provider="kimi", enabled=True)
    try:
        asyncio.run(call_model(model=m, prompt="hi"))
        assert False
    except ValueError as e:
        assert "missing api key" in str(e)


def test_call_model_kimi_uses_openai_compatible_api(monkeypatch):
    from app.core.config import settings
    from app.models.model_config import ModelConfig
    from app.services.model_calling import call_model

    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "OK"}}]}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _Resp()

    monkeypatch.setattr("app.services.model_calling.httpx.AsyncClient", lambda timeout=60: _Client())
    monkeypatch.setattr(settings, "kimi_api_key", "secret")
    monkeypatch.setattr(settings, "kimi_base_url", "https://api.moonshot.cn/v1")
    monkeypatch.setattr(settings, "kimi_temperature", 0.15)
    monkeypatch.setattr(settings, "kimi_max_tokens", 456)

    m = ModelConfig(model_id="kimi-k2.6", name="x", provider="kimi", enabled=True)
    result = asyncio.run(call_model(model=m, prompt="hello"))

    assert result == "OK"
    assert captured["url"] == "https://api.moonshot.cn/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert captured["json"]["model"] == "kimi-k2.6"
    assert captured["json"]["messages"][-1]["content"] == "hello"
    assert captured["json"]["temperature"] == 0.15
    assert captured["json"]["max_tokens"] == 456


def test_call_model_xiaomimimo_missing_key_raises():
    from app.models.model_config import ModelConfig
    from app.services.model_calling import call_model

    m = ModelConfig(model_id="mimo-v2.5-pro", name="x", provider="xiaomimimo", enabled=True)
    try:
        asyncio.run(call_model(model=m, prompt="hi"))
        assert False
    except ValueError as e:
        assert "missing api key" in str(e)


def test_call_model_xiaomimimo_uses_openai_compatible_api(monkeypatch):
    from app.core.config import settings
    from app.models.model_config import ModelConfig
    from app.services.model_calling import call_model

    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "OK"}}]}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _Resp()

    monkeypatch.setattr("app.services.model_calling.httpx.AsyncClient", lambda timeout=60: _Client())
    monkeypatch.setattr(settings, "xiaomimimo_api_key", "secret")
    monkeypatch.setattr(settings, "xiaomimimo_base_url", "https://token-plan-cn.xiaomimimo.com/v1")
    monkeypatch.setattr(settings, "xiaomimimo_temperature", 0.25)
    monkeypatch.setattr(settings, "xiaomimimo_max_tokens", 321)

    m = ModelConfig(model_id="mimo-v2.5-pro", name="x", provider="xiaomimimo", enabled=True)
    result = asyncio.run(call_model(model=m, prompt="hello"))

    assert result == "OK"
    assert captured["url"] == "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert captured["json"]["model"] == "mimo-v2.5-pro"
    assert captured["json"]["messages"][-1]["content"] == "hello"
    assert captured["json"]["temperature"] == 0.25
    assert captured["json"]["max_tokens"] == 321


def test_call_model_anthropic_missing_key_raises():
    from app.models.model_config import ModelConfig
    from app.services.model_calling import call_model

    m = ModelConfig(
        model_id="claude-3-5-sonnet-20240620", name="x", provider="anthropic", enabled=True, params_json='{"max_tokens":123}'
    )
    try:
        asyncio.run(call_model(model=m, prompt="hi"))
        assert False
    except ValueError as e:
        assert "missing api key" in str(e)
