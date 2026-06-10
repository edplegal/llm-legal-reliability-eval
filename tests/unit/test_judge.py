"""Tests for Phase 3: judge module."""

from __future__ import annotations

import pytest

from ai_eval.judge import build_judge_prompt, extract_json


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
