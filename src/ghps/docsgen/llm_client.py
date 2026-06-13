"""Provider-agnostic LLM seam for doc generation.

`complete_json(system, user) -> dict` is the only method generators depend on.
Two adapters, both built on `requests` (no vendor SDKs):
  - DashScopeClient  — Alibaba Qwen via the OpenAI-compatible endpoint (v1).
  - AnthropicClient  — Claude via the Messages API (the cost/quality dial).

`get_client()` reads env so model choice is a per-run dial, not a commitment.
Keys never live in code; for this PUBLIC repo they come from a gitignored .env
locally and GitHub Actions secrets in CI.
"""

from __future__ import annotations

import json
import os
from typing import Protocol

import requests

_TIMEOUT = 120
_MAX_TOKENS = 4096


class LLMClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str) -> dict:
        """Return a parsed JSON object from the model."""
        ...


def _extract_json(text: str) -> dict:
    """Parse a JSON object from model text, tolerating ``` fences.

    Handles ```json / ``` (with or without a leading newline), an inline
    one-line fence, and unfenced JSON. Strips the opening fence + optional
    ``json`` language tag and the closing fence, then json.loads the remainder.
    """
    s = text.strip()
    if s.startswith("```"):
        s = s[3:]
        if s[:4].lower() == "json":
            s = s[4:]
        if s.endswith("```"):
            s = s[:-3]
    return json.loads(s.strip())


class DashScopeClient:
    """Alibaba Qwen via the DashScope OpenAI-compatible chat-completions API."""

    def __init__(self, api_key: str, base_url: str, model: str, session=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._session = session or requests.Session()

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(content)


class AnthropicClient:
    """Claude via the Anthropic Messages API."""

    def __init__(self, api_key: str, base_url: str, model: str, session=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._session = session or requests.Session()

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._session.post(
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": _MAX_TOKENS,
                "system": system + "\n\nRespond with a single JSON object only.",
                "messages": [{"role": "user", "content": user}],
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        return _extract_json(text)


def get_client(provider: str | None = None) -> LLMClient:
    """Construct an LLM client from env (provider defaults to $LLM_PROVIDER)."""
    provider = (provider or os.environ.get("LLM_PROVIDER", "dashscope")).lower()

    if provider == "dashscope":
        key = os.environ.get("DASHSCOPE_API_KEY")
        if not key:
            raise RuntimeError("DASHSCOPE_API_KEY is not set")
        return DashScopeClient(
            api_key=key,
            base_url=os.environ.get(
                "DASHSCOPE_BASE_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ),
            model=os.environ.get("DASHSCOPE_MODEL", "qwen-plus"),
        )

    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return AnthropicClient(
            api_key=key,
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        )

    raise RuntimeError(f"unknown LLM provider: {provider}")
