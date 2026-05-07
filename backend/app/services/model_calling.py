from __future__ import annotations

import os
import json
from typing import Any, Dict

import httpx

from app.core.config import settings
from app.models.model_config import ModelConfig


def _get_api_key(model: ModelConfig) -> str:
    if model.api_key_env:
        k = os.environ.get(model.api_key_env)
        if k:
            return k
    if model.provider == "openai" and settings.openai_api_key:
        return settings.openai_api_key
    if model.provider == "anthropic" and settings.anthropic_api_key:
        return settings.anthropic_api_key
    if model.provider == "kimi" and settings.kimi_api_key:
        return settings.kimi_api_key
    if model.provider == "xiaomimimo" and settings.xiaomimimo_api_key:
        return settings.xiaomimimo_api_key
    raise ValueError("missing api key")


def _model_params(model: ModelConfig) -> Dict[str, Any]:
    if not model.params_json:
        return {}
    try:
        data = json.loads(model.params_json)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


async def _call_openai_compatible(*, model: ModelConfig, prompt: str, base_url: str, temperature: float, max_tokens: int) -> str:
    key = _get_api_key(model)
    headers = {"authorization": f"Bearer {key}"}
    params = _model_params(model)
    system_prompt = model.system_prompt or params.get("system_prompt")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model.model_id,
        "messages": messages,
        "temperature": params.get("temperature", temperature),
        "max_tokens": params.get("max_tokens", max_tokens),
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise ValueError("invalid openai-compatible response schema") from e


async def call_model(*, model: ModelConfig, prompt: str) -> str:
    if model.provider == "mock":
        return f"[mock:{model.model_id}] {prompt}"

    if model.provider == "http":
        if not model.base_url:
            raise ValueError("base_url is required for http provider")
        headers: dict[str, str] = {}
        if model.api_key_env:
            key = os.environ.get(model.api_key_env)
            if key:
                headers["authorization"] = f"Bearer {key}"

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(model.base_url, json={"prompt": prompt, "model_id": model.model_id}, headers=headers)
            r.raise_for_status()
            data = r.json()
            content = data.get("content")
            if not isinstance(content, str):
                raise ValueError("invalid response schema: missing content")
            return content

    if model.provider == "openai":
        base_url = model.base_url or settings.openai_base_url
        return await _call_openai_compatible(
            model=model,
            prompt=prompt,
            base_url=base_url,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
        )

    if model.provider == "kimi":
        base_url = model.base_url or settings.kimi_base_url
        return await _call_openai_compatible(
            model=model,
            prompt=prompt,
            base_url=base_url,
            temperature=settings.kimi_temperature,
            max_tokens=settings.kimi_max_tokens,
        )

    if model.provider == "xiaomimimo":
        base_url = model.base_url or settings.xiaomimimo_base_url
        return await _call_openai_compatible(
            model=model,
            prompt=prompt,
            base_url=base_url,
            temperature=settings.xiaomimimo_temperature,
            max_tokens=settings.xiaomimimo_max_tokens,
        )

    if model.provider == "anthropic":
        key = _get_api_key(model)
        base_url = model.base_url or settings.anthropic_base_url
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        params = _model_params(model)
        max_tokens = params.get("max_tokens", settings.anthropic_max_tokens)
        system_prompt = model.system_prompt or params.get("system_prompt")
        payload = {
            "model": model.model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{base_url}/messages", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            try:
                parts = data["content"]
                if not parts:
                    return ""
                text = parts[0].get("text")
                if not isinstance(text, str):
                    raise ValueError("invalid anthropic response schema")
                return text
            except Exception as e:
                raise ValueError("invalid anthropic response schema") from e

    raise ValueError(f"unsupported provider: {model.provider}")
