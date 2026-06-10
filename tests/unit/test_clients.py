"""Tests for the shared provider API clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import MagicMock, patch

import pytest

from ai_eval.clients import call_anthropic, call_google, call_openai

if TYPE_CHECKING:
    from ai_eval.schema import ModelConfig


def _mock_response(payload: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture()
def api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")


@pytest.mark.usefixtures("api_keys")
class TestCallOpenai:
    CONFIG: ClassVar[ModelConfig] = {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1/chat/completions",
    }

    def test_normalizes_payload(self) -> None:
        payload = {
            "choices": [{"message": {"content": "Answer."}}],
            "model": "gpt-4o-2024-08-06",
            "usage": {"total_tokens": 42},
        }
        with patch(
            "ai_eval.clients.requests.post",
            return_value=_mock_response(payload),
        ) as post:
            result = call_openai(
                "Q?",
                self.CONFIG,
                system_prompt="sys",
                temperature=0.7,
                max_tokens=100,
            )

        assert result == {
            "text": "Answer.",
            "model_version": "gpt-4o-2024-08-06",
            "tokens_used": 42,
        }
        body = post.call_args.kwargs["json"]
        assert body["messages"][0] == {"role": "system", "content": "sys"}
        auth = post.call_args.kwargs["headers"]["Authorization"]
        assert auth == "Bearer sk-openai-test"


@pytest.mark.usefixtures("api_keys")
class TestCallAnthropic:
    CONFIG: ClassVar[ModelConfig] = {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1/messages",
    }

    def test_normalizes_payload(self) -> None:
        payload = {
            "content": [{"text": "Answer."}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 30, "output_tokens": 12},
        }
        with patch(
            "ai_eval.clients.requests.post",
            return_value=_mock_response(payload),
        ) as post:
            result = call_anthropic(
                "Q?",
                self.CONFIG,
                system_prompt="sys",
                temperature=0.0,
                max_tokens=100,
            )

        assert result["text"] == "Answer."
        assert result["tokens_used"] == 42
        headers = post.call_args.kwargs["headers"]
        assert headers["x-api-key"] == "sk-ant-test"
        assert post.call_args.kwargs["json"]["system"] == "sys"


@pytest.mark.usefixtures("api_keys")
class TestCallGoogle:
    CONFIG: ClassVar[ModelConfig] = {
        "provider": "google",
        "model": "gemini-2.5-flash",
        "api_key_env": "GOOGLE_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
    }

    def test_normalizes_payload(self) -> None:
        payload = {
            "candidates": [{"content": {"parts": [{"text": "Answer."}]}}],
            "modelVersion": "gemini-2.5-flash-002",
            "usageMetadata": {"totalTokenCount": 55},
        }
        with patch(
            "ai_eval.clients.requests.post",
            return_value=_mock_response(payload),
        ) as post:
            result = call_google(
                "Q?",
                self.CONFIG,
                system_prompt="sys",
                temperature=0.7,
                max_tokens=100,
            )

        assert result == {
            "text": "Answer.",
            "model_version": "gemini-2.5-flash-002",
            "tokens_used": 55,
        }
        url = post.call_args.args[0]
        assert url.endswith("gemini-2.5-flash:generateContent")

    def test_api_key_in_header_never_in_url(self) -> None:
        """The Gemini key must travel via x-goog-api-key, not the query
        string, so it can't leak into proxy or server logs."""
        payload = {
            "candidates": [{"content": {"parts": [{"text": "x"}]}}],
        }
        with patch(
            "ai_eval.clients.requests.post",
            return_value=_mock_response(payload),
        ) as post:
            call_google(
                "Q?",
                self.CONFIG,
                system_prompt="sys",
                temperature=0.7,
                max_tokens=100,
            )

        url = post.call_args.args[0]
        headers = post.call_args.kwargs["headers"]
        assert "goog-test" not in url
        assert headers["x-goog-api-key"] == "goog-test"
