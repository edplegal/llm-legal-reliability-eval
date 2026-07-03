"""Tests for the shared provider API clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import MagicMock, patch

import pytest
import requests

from ai_eval.clients import (
    _http_error_detail,
    call_anthropic,
    call_google,
    call_openai,
)

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
                max_tokens=100,
            )

        assert result == {
            "text": "Answer.",
            "model_version": "gpt-4o-2024-08-06",
            "tokens_used": 42,
        }
        body = post.call_args.kwargs["json"]
        assert body["messages"][0] == {"role": "system", "content": "sys"}
        # GPT-5.x contract: max_completion_tokens, and no sampling params.
        assert body["max_completion_tokens"] == 100
        assert "max_tokens" not in body
        assert "temperature" not in body
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
                max_tokens=100,
            )

        assert result["text"] == "Answer."
        assert result["tokens_used"] == 42
        headers = post.call_args.kwargs["headers"]
        assert headers["x-api-key"] == "sk-ant-test"
        body = post.call_args.kwargs["json"]
        assert body["system"] == "sys"
        # Claude 5 contract: no sampling params sent.
        assert "temperature" not in body

    def test_skips_thinking_blocks(self) -> None:
        """Claude 5 adaptive thinking prepends thinking blocks; the answer
        is the first text block, not content[0]."""
        payload = {
            "content": [
                {"type": "thinking", "thinking": ""},
                {"type": "text", "text": "Answer."},
            ],
            "model": "claude-sonnet-5",
            "usage": {"input_tokens": 30, "output_tokens": 12},
        }
        with patch(
            "ai_eval.clients.requests.post",
            return_value=_mock_response(payload),
        ):
            result = call_anthropic(
                "Q?",
                self.CONFIG,
                system_prompt="sys",
                max_tokens=100,
            )
        assert result["text"] == "Answer."

    def test_no_text_block_raises_key_error(self) -> None:
        """A content list with no text block raises KeyError so the retry
        wrapper treats it like any other malformed payload."""
        payload = {
            "content": [{"type": "thinking", "thinking": ""}],
            "model": "claude-sonnet-5",
            "usage": {"input_tokens": 30, "output_tokens": 12},
        }
        with (
            patch(
                "ai_eval.clients.requests.post",
                return_value=_mock_response(payload),
            ),
            pytest.raises(KeyError, match="no text block"),
        ):
            call_anthropic(
                "Q?",
                self.CONFIG,
                system_prompt="sys",
                max_tokens=100,
            )


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
                max_tokens=100,
            )

        assert result == {
            "text": "Answer.",
            "model_version": "gemini-2.5-flash-002",
            "tokens_used": 55,
        }
        url = post.call_args.args[0]
        assert url.endswith("gemini-2.5-flash:generateContent")
        gen_config = post.call_args.kwargs["json"]["generationConfig"]
        assert "temperature" not in gen_config

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
                max_tokens=100,
            )

        url = post.call_args.args[0]
        headers = post.call_args.kwargs["headers"]
        assert "goog-test" not in url
        assert headers["x-goog-api-key"] == "goog-test"


@pytest.mark.usefixtures("api_keys")
class TestPerModelTemperature:
    """The optional per-model temperature (bridge-run replication only)."""

    def test_openai_sends_configured_temperature(self) -> None:
        cfg: ModelConfig = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1/chat/completions",
            "temperature": 0.0,
        }
        payload = {
            "choices": [{"message": {"content": "x"}}],
            "model": "gpt-4o",
            "usage": {"total_tokens": 1},
        }
        with patch(
            "ai_eval.clients.requests.post",
            return_value=_mock_response(payload),
        ) as post:
            call_openai("Q?", cfg, system_prompt="sys", max_tokens=100)
        assert post.call_args.kwargs["json"]["temperature"] == 0.0

    def test_google_sends_configured_temperature(self) -> None:
        cfg: ModelConfig = {
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key_env": "GOOGLE_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
            "temperature": 0.0,
        }
        payload = {"candidates": [{"content": {"parts": [{"text": "x"}]}}]}
        with patch(
            "ai_eval.clients.requests.post",
            return_value=_mock_response(payload),
        ) as post:
            call_google("Q?", cfg, system_prompt="sys", max_tokens=100)
        gen = post.call_args.kwargs["json"]["generationConfig"]
        assert gen["temperature"] == 0.0


class TestHttpErrorDetail:
    """Tests for the 429-diagnosability helper on retry warnings."""

    def test_includes_body_and_retry_after(self) -> None:
        resp = MagicMock()
        resp.headers = {"retry-after": "17"}
        resp.text = '{"error": {"type": "insufficient_quota"}}'
        exc = requests.HTTPError(response=resp)
        detail = _http_error_detail(exc)
        assert "retry-after=17s" in detail
        assert "insufficient_quota" in detail

    def test_non_http_error_yields_empty_string(self) -> None:
        assert _http_error_detail(KeyError("parts")) == ""

    def test_http_error_without_response_yields_empty_string(self) -> None:
        assert _http_error_detail(requests.HTTPError()) == ""
