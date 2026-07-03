"""Tests for Phase 3: judge module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
import requests

from ai_eval.judge import (
    build_judge_prompt,
    call_judge_with_retry,
    extract_json,
    validate_scores,
)

if TYPE_CHECKING:
    from ai_eval.schema import ModelConfig, ProviderResult


class TestBuildJudgePrompt:
    """Tests for judge prompt construction."""

    def test_injects_both_placeholders(self) -> None:
        """Template has both prompt_text and response_text replaced."""
        template = "Prompt: {prompt_text}\nResponse: {response_text}"
        result = build_judge_prompt(template, "my question", "my answer")
        assert result == "Prompt: my question\nResponse: my answer"

    def test_preserves_surrounding_text(self) -> None:
        """Non-placeholder text is preserved."""
        template = "START {prompt_text} MIDDLE {response_text} END"
        result = build_judge_prompt(template, "Q", "A")
        assert result == "START Q MIDDLE A END"


class TestExtractJson:
    """Tests for JSON extraction from model responses."""

    def test_parses_clean_json(self) -> None:
        """Direct JSON string is parsed correctly."""
        raw = '{"disclaimer": {"score": 4, "justification": "Good."}}'
        result = extract_json(raw)
        assert result["disclaimer"]["score"] == 4

    def test_extracts_from_markdown_fence(self) -> None:
        """JSON inside markdown code fences is extracted."""
        inner = '{"disclaimer": {"score": 3, "justification": "OK."}}'
        raw = f"Some preamble\n```json\n{inner}\n```"
        result = extract_json(raw)
        assert result["disclaimer"]["score"] == 3

    def test_extracts_from_braces(self) -> None:
        """JSON found between first { and last } is extracted."""
        inner = '{"disclaimer": {"score": 5, "justification": "Excellent."}}'
        raw = f"Here is my evaluation:\n{inner}\nEnd."
        result = extract_json(raw)
        assert result["disclaimer"]["score"] == 5

    def test_raises_on_invalid_json(self) -> None:
        """Non-JSON text raises ValueError."""
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            extract_json("This is not JSON at all.")

    def test_handles_whitespace(self) -> None:
        """Leading/trailing whitespace doesn't break parsing."""
        raw = '  \n  {"disclaimer": {"score": 2, "justification": "Minimal."}}  \n  '
        result = extract_json(raw)
        assert result["disclaimer"]["score"] == 2


class TestValidateScores:
    """Tests for the rubric-shape gate on judge output."""

    def test_nested_shape_passes_through(self) -> None:
        parsed = {"disclaimer": {"score": 4, "justification": "ok"}}
        assert validate_scores(parsed) is parsed

    def test_missing_dimensions_are_allowed(self) -> None:
        assert validate_scores({}) == {}

    def test_flat_int_dimension_raises(self) -> None:
        with pytest.raises(ValueError, match="expected an object"):
            validate_scores({"guardrail": 3})

    def test_out_of_range_score_raises(self) -> None:
        with pytest.raises(ValueError, match=r"expected int 0\.\.5"):
            validate_scores({"disclaimer": {"score": 7, "justification": "x"}})

    def test_string_score_raises(self) -> None:
        with pytest.raises(ValueError, match=r"expected int 0\.\.5"):
            validate_scores({"disclaimer": {"score": "4", "justification": "x"}})

    def test_wrong_shape_triggers_reask_then_null(
        self, monkeypatch: pytest.MonkeyPatch, judge_config: ModelConfig
    ) -> None:
        """A judge that keeps emitting flat scores ends as null, not as a
        malformed record in the dataset."""
        flat = '{"disclaimer": 4, "escalation": 3}'
        mock = Mock(side_effect=[_provider_result(flat), _provider_result(flat)])
        monkeypatch.setattr("ai_eval.judge.call_model_with_retry", mock)
        scores, _ = call_judge_with_retry("judge prompt", "claude", judge_config, 4096)
        assert scores is None
        assert mock.call_count == 2


@pytest.fixture
def judge_config() -> ModelConfig:
    """A minimal judge ModelConfig; the provider call is mocked, so values are inert."""
    return {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://example.test/v1/messages",
    }


def _provider_result(text: str, version: str = "claude-sonnet-4-6") -> ProviderResult:
    """Build a ProviderResult stand-in for a mocked judge API call."""
    return {"text": text, "model_version": version, "tokens_used": 10}


class TestCallJudgeWithRetry:
    """Tests for the judge call + parse-retry wrapper."""

    def test_valid_json_first_call_returns_parsed_scores(
        self, monkeypatch: pytest.MonkeyPatch, judge_config: ModelConfig
    ) -> None:
        """A parseable first response yields scores and the model version."""
        valid = '{"disclaimer": {"score": 4, "justification": "Good."}}'
        mock = Mock(return_value=_provider_result(valid, "claude-sonnet-4-6"))
        monkeypatch.setattr("ai_eval.judge.call_model_with_retry", mock)

        scores, version = call_judge_with_retry(
            "judge prompt", "claude", judge_config, 4096
        )

        assert scores is not None
        assert scores["disclaimer"]["score"] == 4
        assert version == "claude-sonnet-4-6"
        assert mock.call_count == 1

    def test_unparseable_then_valid_reasks_and_succeeds(
        self, monkeypatch: pytest.MonkeyPatch, judge_config: ModelConfig
    ) -> None:
        """An unparseable response is re-asked; a later valid one is parsed."""
        valid = '{"disclaimer": {"score": 3, "justification": "OK."}}'
        mock = Mock(side_effect=[_provider_result("not json"), _provider_result(valid)])
        monkeypatch.setattr("ai_eval.judge.call_model_with_retry", mock)

        scores, _ = call_judge_with_retry("judge prompt", "claude", judge_config, 4096)

        assert scores is not None
        assert scores["disclaimer"]["score"] == 3
        assert mock.call_count == 2

    def test_unparseable_every_attempt_returns_null_with_version(
        self, monkeypatch: pytest.MonkeyPatch, judge_config: ModelConfig
    ) -> None:
        """Exhausting parse attempts stores null but keeps the model version."""
        mock = Mock(
            side_effect=[
                _provider_result("nope", "gemini-2.5-flash"),
                _provider_result("still nope", "gemini-2.5-flash"),
            ]
        )
        monkeypatch.setattr("ai_eval.judge.call_model_with_retry", mock)

        scores, version = call_judge_with_retry(
            "judge prompt", "gemini", judge_config, 4096
        )

        assert scores is None
        assert version == "gemini-2.5-flash"
        assert mock.call_count == 2

    def test_transport_failure_after_retries_returns_null(
        self, monkeypatch: pytest.MonkeyPatch, judge_config: ModelConfig
    ) -> None:
        """A transport error that survives backoff yields null and no version."""
        mock = Mock(side_effect=requests.RequestException("503 Service Unavailable"))
        monkeypatch.setattr("ai_eval.judge.call_model_with_retry", mock)

        scores, version = call_judge_with_retry(
            "judge prompt", "gemini", judge_config, 4096
        )

        assert scores is None
        assert version is None
        assert mock.call_count == 1
