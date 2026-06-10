"""Tests for Phase 2: blind module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ai_eval.blind import (
    blind,
    deterministic_response_id,
    scan_for_self_identification,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestDeterministicResponseId:
    """Tests for content-derived response IDs."""

    def test_format_matches_pattern(self) -> None:
        """Generated ID follows R-<12 hex chars> format."""
        rid = deterministic_response_id(1, "chatgpt", 0, "Some response.")
        assert rid.startswith("R-")
        assert len(rid) == 14
        assert all(c in "0123456789abcdef" for c in rid[2:])

    def test_same_input_same_id(self) -> None:
        """Re-blinding identical content yields the identical ID, so judge
        scores keyed on response_id survive a re-blind."""
        a = deterministic_response_id(3, "claude", 1, "Answer text.")
        b = deterministic_response_id(3, "claude", 1, "Answer text.")
        assert a == b

    def test_different_text_different_id(self) -> None:
        a = deterministic_response_id(1, "chatgpt", 0, "Answer A.")
        b = deterministic_response_id(1, "chatgpt", 0, "Answer B.")
        assert a != b

    def test_sample_idx_distinguishes_identical_text(self) -> None:
        """Two samples of the same cell with identical text get distinct IDs."""
        a = deterministic_response_id(1, "chatgpt", 0, "Same text.")
        b = deterministic_response_id(1, "chatgpt", 1, "Same text.")
        assert a != b

    def test_model_distinguishes_identical_text(self) -> None:
        a = deterministic_response_id(1, "chatgpt", 0, "Same text.")
        b = deterministic_response_id(1, "claude", 0, "Same text.")
        assert a != b


class TestScanForSelfIdentification:
    """Tests for self-identification detection."""

    def test_detects_chatgpt_self_id(self) -> None:
        """Catches 'I'm ChatGPT' pattern."""
        warnings = scan_for_self_identification(
            "I'm ChatGPT and I can help you.", "R-test1", "chatgpt"
        )
        assert len(warnings) >= 1
        assert "ChatGPT" in warnings[0]

    def test_detects_claude_self_id(self) -> None:
        """Catches 'as Claude' pattern."""
        warnings = scan_for_self_identification(
            "As Claude, I should note...", "R-test2", "claude"
        )
        assert len(warnings) >= 1
        assert "Claude" in warnings[0]

    def test_detects_ai_language_model(self) -> None:
        """Catches 'as an AI language model' pattern."""
        warnings = scan_for_self_identification(
            "As an AI language model, I cannot provide legal advice.",
            "R-test3",
            "gemini",
        )
        assert len(warnings) >= 1

    def test_no_false_positives(self) -> None:
        """Clean text produces no warnings."""
        warnings = scan_for_self_identification(
            "You should consult an attorney about this matter.",
            "R-clean",
            "chatgpt",
        )
        assert len(warnings) == 0

    def test_detects_made_by_pattern(self) -> None:
        """Catches 'made by OpenAI' pattern."""
        warnings = scan_for_self_identification(
            "I was made by OpenAI.", "R-test4", "chatgpt"
        )
        assert len(warnings) >= 1

    def test_case_insensitive(self) -> None:
        """Detection is case-insensitive."""
        warnings = scan_for_self_identification("i'm chatgpt", "R-test5", "chatgpt")
        assert len(warnings) >= 1

    @pytest.mark.parametrize(
        "text",
        [
            "GPT-4o would approach this differently.",
            "I was trained by Google to be helpful.",
            "OpenAI's usage policies prevent me from answering.",
            "As a large language model, I have limitations.",
            "Claude 3.5 has a knowledge cutoff.",
            "I'm Bard, Google's conversational AI.",
            "This model was developed by Anthropic.",
        ],
    )
    def test_detects_expanded_patterns(self, text: str) -> None:
        """Version strings and vendor possessives are caught too."""
        assert scan_for_self_identification(text, "R-exp", "any")


class TestBlindPipeline:
    """End-to-end tests of blind() against a temp project root."""

    @staticmethod
    def _write_raw(base: Path, entries: list[dict[str, object]]) -> None:
        data = base / "data"
        data.mkdir(parents=True, exist_ok=True)
        (data / "raw_responses.json").write_text(json.dumps(entries))

    @staticmethod
    def _raw_entry(
        prompt_id: int, model_id: str, sample_idx: int, text: str
    ) -> dict[str, object]:
        return {
            "prompt_id": prompt_id,
            "model_id": model_id,
            "sample_idx": sample_idx,
            "response_text": text,
            "timestamp": "2026-06-10T00:00:00+00:00",
        }

    def test_lookup_carries_sample_idx(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every lookup entry records which sample produced the response."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        self._write_raw(
            tmp_path,
            [
                self._raw_entry(1, "chatgpt", 0, "Answer one."),
                self._raw_entry(1, "chatgpt", 1, "Answer two."),
            ],
        )
        blind()
        lookup = json.loads((tmp_path / "data" / "blind_lookup.json").read_text())
        assert sorted(e["sample_idx"] for e in lookup.values()) == [0, 1]

    def test_reblind_is_byte_identical(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Re-running blind on unchanged raw data rewrites nothing and
        rotates nothing to legacy."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        self._write_raw(
            tmp_path,
            [
                self._raw_entry(1, "chatgpt", 0, "Answer A."),
                self._raw_entry(1, "claude", 0, "Answer B."),
            ],
        )
        blind()
        data = tmp_path / "data"
        first = (data / "blinded_responses.json").read_text()
        blind()
        assert (data / "blinded_responses.json").read_text() == first
        assert not (data / "legacy").exists()

    def test_duplicate_raw_entries_raise_value_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exact duplicate rows in raw_responses.json are a hard error."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        entry = self._raw_entry(1, "chatgpt", 0, "Twin answer.")
        self._write_raw(tmp_path, [entry, dict(entry)])
        with pytest.raises(ValueError, match="Duplicate response content"):
            blind()

    def test_orphaned_judge_scores_rotated_to_legacy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Judge scores referencing IDs absent from the new lookup are moved
        to legacy instead of being left to mis-join downstream."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        self._write_raw(tmp_path, [self._raw_entry(1, "chatgpt", 0, "Fresh answer.")])
        data = tmp_path / "data"
        (data / "judge_scores.json").write_text(
            json.dumps(
                [
                    {
                        "response_id": "R-deadbeef0000",
                        "prompt_id": 1,
                        "judge_model": "claude",
                        "scores": None,
                    }
                ]
            )
        )
        blind()
        assert not (data / "judge_scores.json").exists()
        rotated = list((data / "legacy").glob("judge_scores_*.json"))
        assert len(rotated) == 1

    def test_matching_judge_scores_left_in_place(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Judge scores that still join to the new lookup are untouched."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        self._write_raw(tmp_path, [self._raw_entry(1, "chatgpt", 0, "Stable answer.")])
        rid = deterministic_response_id(1, "chatgpt", 0, "Stable answer.")
        data = tmp_path / "data"
        data.mkdir(exist_ok=True)
        (data / "judge_scores.json").write_text(
            json.dumps(
                [
                    {
                        "response_id": rid,
                        "prompt_id": 1,
                        "judge_model": "claude",
                        "scores": None,
                    }
                ]
            )
        )
        blind()
        assert (data / "judge_scores.json").exists()
