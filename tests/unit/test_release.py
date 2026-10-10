"""Tests for the reproducibility hooks: timestamp override and in-memory analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

from ai_eval.analyze import compute_results, compute_run_metadata
from ai_eval.paths import generated_at_stamp

PROMPTS: dict[int, dict[str, Any]] = {1: {"id": 1, "category": "info_vs_crisis"}}


class TestGeneratedAt:
    """The environment override makes outputs byte-reproducible."""

    def test_generated_at_stamp_uses_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_EVAL_GENERATED_AT", "2026-07-08T00:00:00+00:00")
        assert generated_at_stamp() == "2026-07-08T00:00:00+00:00"

    def test_generated_at_stamp_defaults_to_now(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AI_EVAL_GENERATED_AT", raising=False)
        assert generated_at_stamp().startswith("20")

    def test_explicit_argument_beats_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_judge_scores: list[dict[str, Any]],
        sample_blind_lookup: dict[str, dict[str, Any]],
    ) -> None:
        monkeypatch.setenv("AI_EVAL_GENERATED_AT", "from-env")
        meta = compute_run_metadata(
            sample_judge_scores, sample_blind_lookup, PROMPTS, "explicit"
        )
        assert meta["generated_at"] == "explicit"
        assert (
            compute_run_metadata(sample_judge_scores, sample_blind_lookup, PROMPTS)[
                "generated_at"
            ]
            == "from-env"
        )


class TestComputeResults:
    """The in-memory analysis is deterministic and complete."""

    def test_compute_results_is_deterministic(
        self,
        sample_judge_scores: list[dict[str, Any]],
        sample_blind_lookup: dict[str, dict[str, Any]],
    ) -> None:
        a = compute_results(sample_judge_scores, sample_blind_lookup, PROMPTS, "t")
        b = compute_results(sample_judge_scores, sample_blind_lookup, PROMPTS, "t")
        assert a == b
        assert set(a) >= {
            "metadata",
            "model_averages",
            "self_favoritism",
            "variance_components",
        }
