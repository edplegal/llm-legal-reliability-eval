"""Tests for Phase 1: collect module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

    from ai_eval.schema import ModelConfig

import pytest
import requests

from ai_eval.collect import (
    call_model_with_retry,
    collect,
    get_completed_keys,
    load_existing_responses,
)

MOCK_CONFIG: ModelConfig = {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key_env": "OPENAI_API_KEY",
    "base_url": "https://api.openai.com/v1/chat/completions",
}


class TestCallModelWithRetry:
    """Tests for the retry logic in call_model_with_retry."""

    def test_success_on_first_attempt(self) -> None:
        """Happy path: API call succeeds immediately."""
        expected = {
            "text": "Hello!",
            "model_version": "gpt-4o",
            "tokens_used": 100,
        }
        mock_caller = MagicMock(return_value=expected)

        with patch.dict(
            "ai_eval.clients.PROVIDER_CALLERS",
            {"openai": mock_caller},
        ):
            result = call_model_with_retry(
                "test prompt",
                "chatgpt",
                MOCK_CONFIG,
                system_prompt="You are a helpful assistant.",
                max_tokens=2048,
            )

        assert result == expected
        mock_caller.assert_called_once()

    def test_retries_on_request_exception(self) -> None:
        """API call fails then succeeds on retry."""
        expected = {
            "text": "Recovered!",
            "model_version": "gpt-4o",
            "tokens_used": 150,
        }
        mock_caller = MagicMock(
            side_effect=[
                requests.RequestException("timeout"),
                expected,
            ]
        )

        with (
            patch.dict(
                "ai_eval.clients.PROVIDER_CALLERS",
                {"openai": mock_caller},
            ),
            patch("ai_eval.clients.time.sleep"),
        ):
            result = call_model_with_retry(
                "test prompt",
                "chatgpt",
                MOCK_CONFIG,
                system_prompt="You are a helpful assistant.",
                max_tokens=2048,
            )

        assert result == expected
        assert mock_caller.call_count == 2

    def test_raises_after_max_retries(self) -> None:
        """All retries exhausted raises the exception."""
        mock_caller = MagicMock(
            side_effect=requests.RequestException("persistent failure")
        )

        with (
            patch.dict(
                "ai_eval.clients.PROVIDER_CALLERS",
                {"openai": mock_caller},
            ),
            patch("ai_eval.clients.time.sleep"),
            pytest.raises(
                requests.RequestException,
                match="persistent failure",
            ),
        ):
            call_model_with_retry(
                "test prompt",
                "chatgpt",
                MOCK_CONFIG,
                system_prompt="You are a helpful assistant.",
                max_tokens=2048,
            )


class TestCollectValidation:
    """Tests for collect() input validation."""

    def test_collect_zero_samples_raises_value_error(self) -> None:
        """samples < 1 is rejected before any IO happens."""
        with pytest.raises(ValueError, match="samples must be >= 1"):
            collect(samples=0)


class TestResumeSupport:
    """Tests for resume/skip logic."""

    def test_load_existing_responses_file_exists(self, tmp_path: Path) -> None:
        """Loads responses from existing file and back-fills sample_idx=0
        for entries written before multi-sample support was added."""
        data = [{"prompt_id": 1, "model_id": "chatgpt"}]
        path = tmp_path / "raw_responses.json"
        with path.open("w") as f:
            json.dump(data, f)

        result = load_existing_responses(path)
        assert result == [{"prompt_id": 1, "model_id": "chatgpt", "sample_idx": 0}]

    def test_load_existing_responses_file_missing(self, tmp_path: Path) -> None:
        """Returns empty list when file doesn't exist."""
        path = tmp_path / "nonexistent.json"
        result = load_existing_responses(path)
        assert result == []

    def test_get_completed_keys_defaults_sample_idx(self) -> None:
        """Extracts (prompt_id, model_id, sample_idx) tuples; legacy entries
        without sample_idx default to 0."""
        responses: list[Any] = [
            {"prompt_id": 1, "model_id": "chatgpt"},
            {"prompt_id": 1, "model_id": "claude"},
            {"prompt_id": 2, "model_id": "gemini"},
        ]
        keys = get_completed_keys(responses)
        assert keys == {
            (1, "chatgpt", 0),
            (1, "claude", 0),
            (2, "gemini", 0),
        }

    def test_get_completed_keys_respects_sample_idx(self) -> None:
        """Multiple samples per (prompt, model) generate distinct keys."""
        responses: list[Any] = [
            {"prompt_id": 1, "model_id": "chatgpt", "sample_idx": 0},
            {"prompt_id": 1, "model_id": "chatgpt", "sample_idx": 1},
            {"prompt_id": 1, "model_id": "chatgpt", "sample_idx": 2},
        ]
        keys = get_completed_keys(responses)
        assert keys == {
            (1, "chatgpt", 0),
            (1, "chatgpt", 1),
            (1, "chatgpt", 2),
        }
