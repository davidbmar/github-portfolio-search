"""Unit tests for the provider-agnostic LLM client seam (HTTP mocked)."""

from __future__ import annotations

import json

import pytest
from unittest.mock import MagicMock

from ghps.docsgen import llm_client


def _resp(json_data, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    if status_code >= 400:
        r.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return r


class TestDashScopeClient:
    def test_parses_json_object_from_choices(self):
        session = MagicMock()
        payload = {"slug": "demo", "title": "Demo"}
        session.post.return_value = _resp(
            {"choices": [{"message": {"content": json.dumps(payload)}}]}
        )
        client = llm_client.DashScopeClient(
            api_key="k", base_url="https://x/v1", model="qwen-plus", session=session
        )
        result = client.complete_json("sys", "user")
        assert result == payload

    def test_sends_json_response_format(self):
        session = MagicMock()
        session.post.return_value = _resp(
            {"choices": [{"message": {"content": "{}"}}]}
        )
        client = llm_client.DashScopeClient(
            api_key="k", base_url="https://x/v1", model="qwen-plus", session=session
        )
        client.complete_json("sys", "user")
        _, kwargs = session.post.call_args
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        assert kwargs["headers"]["Authorization"] == "Bearer k"


class TestAnthropicClient:
    def test_strips_code_fence_and_parses(self):
        session = MagicMock()
        fenced = "```json\n{\"slug\": \"demo\"}\n```"
        session.post.return_value = _resp({"content": [{"text": fenced}]})
        client = llm_client.AnthropicClient(
            api_key="k", base_url="https://api.anthropic.com", model="claude-x",
            session=session,
        )
        assert client.complete_json("sys", "user") == {"slug": "demo"}


class TestGetClient:
    def test_dashscope_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "dashscope")
        monkeypatch.setenv("DASHSCOPE_API_KEY", "k")
        monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://x/v1")
        monkeypatch.setenv("DASHSCOPE_MODEL", "qwen-plus")
        client = llm_client.get_client()
        assert isinstance(client, llm_client.DashScopeClient)
        assert client.model == "qwen-plus"

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "dashscope")
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
            llm_client.get_client()
