"""Tests for the adversarial null refill."""

from __future__ import annotations

import copy
from typing import Any

from ai_eval.analyze import compute_results
from ai_eval.robustness import (
    applicable_dimensions,
    compare,
    compute_null_refill,
    refill_nulls,
    reported_numbers,
)

PROMPTS: dict[int, dict[str, Any]] = {
    1: {"id": 1, "category": "info_vs_crisis", "pair_id": "P01", "pair_role": "info"}
}


def _with_null(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = copy.deepcopy(scores)
    out[0]["scores"] = None
    return out


class TestRefill:
    """Nulls are refilled only on dimensions the other judges scored."""

    def test_applicable_dimensions_majority_rule(
        self, sample_judge_scores: list[dict[str, Any]]
    ) -> None:
        dims = applicable_dimensions(sample_judge_scores)
        assert dims["R-abc01"] == {
            "disclaimer",
            "escalation",
            "confidence",
            "jurisdiction",
        }

    def test_refill_nulls_fills_applicable_dims_only(
        self, sample_judge_scores: list[dict[str, Any]]
    ) -> None:
        refilled = refill_nulls(_with_null(sample_judge_scores), 5)
        filled = refilled[0]["scores"]
        assert filled["disclaimer"]["score"] == 5
        assert filled["guardrail"]["score"] == 0
        # the input is untouched
        assert _with_null(sample_judge_scores)[0]["scores"] is None

    def test_refill_nulls_leaves_scored_records_alone(
        self, sample_judge_scores: list[dict[str, Any]]
    ) -> None:
        refilled = refill_nulls(sample_judge_scores, 1)
        assert refilled == sample_judge_scores


class TestCompare:
    """The comparison reports the largest movement per family."""

    def test_compare_reports_families_and_flips(
        self,
        sample_judge_scores: list[dict[str, Any]],
        sample_blind_lookup: dict[str, dict[str, Any]],
    ) -> None:
        base = compute_results(sample_judge_scores, sample_blind_lookup, PROMPTS, "x")
        alt = compute_results(
            refill_nulls(_with_null(sample_judge_scores), 5),
            sample_blind_lookup,
            PROMPTS,
            "x",
        )
        comp = compare(base, alt)
        assert set(comp["families"]) >= {"style", "net", "disclaimer_means", "alpha"}
        assert comp["families"]["disclaimer_means"]["max_abs_change"] >= 0
        assert isinstance(comp["significance_flips"], list)
        assert isinstance(comp["core_dimension_ranking_flips"], list)

    def test_reported_numbers_cover_every_judge(
        self,
        sample_judge_scores: list[dict[str, Any]],
        sample_blind_lookup: dict[str, dict[str, Any]],
    ) -> None:
        base = compute_results(sample_judge_scores, sample_blind_lookup, PROMPTS, "x")
        fam, ci = reported_numbers(base)
        assert "style" in fam and any(k.startswith("style/") for k in ci)

    def test_compute_null_refill_structure(
        self,
        sample_judge_scores: list[dict[str, Any]],
        sample_blind_lookup: dict[str, dict[str, Any]],
    ) -> None:
        out = compute_null_refill(
            _with_null(sample_judge_scores), sample_blind_lookup, PROMPTS, "stamp"
        )
        assert out["metadata"]["generated_at"] == "stamp"
        assert out["metadata"]["n_nulls_refilled"] == 1
        assert out["metadata"]["null_judgments_by_judge"] == {"chatgpt": 1}
        assert out["metadata"]["n_bridge_nulls_refilled"] == 0
        assert set(out["refills"]) == {"fill_1", "fill_5"}
        assert "bridge" not in out["refills"]["fill_1"]
