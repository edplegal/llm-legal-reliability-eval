"""Tests for the generational chain under frozen judges."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from ai_eval.bridge import (
    CHAIN_MODELS,
    EraSpec,
    compute_bridge_results,
    compute_crisis_by_era,
    compute_levels,
    compute_steps,
    matched_pairs,
    per_prompt_frozen_scores,
)

PROMPTS: dict[int, dict[str, Any]] = {
    1: {"id": 1, "category": "info_vs_crisis", "pair_id": "P01", "pair_role": "info"},
    2: {"id": 2, "category": "info_vs_crisis", "pair_id": "P01", "pair_role": "crisis"},
    3: {"id": 3, "category": "adversarial_single", "pair_id": None, "pair_role": None},
}


def _scores(disclaimer: int) -> dict[str, Any]:
    return {
        "disclaimer": {"score": disclaimer, "justification": "t"},
        "escalation": {"score": 3, "justification": "t"},
        "confidence": {"score": 3, "justification": "t"},
        "jurisdiction": {"score": 3, "justification": "t"},
        "guardrail": {"score": 0, "justification": "n/a"},
        "regulatory": {"score": 0, "justification": "n/a"},
    }


def _era(
    base: int, judges: tuple[str, ...]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """One response per (prompt, model); disclaimer = base + prompt id, every judge."""
    scores: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    for pid in PROMPTS:
        for model in CHAIN_MODELS:
            rid = f"R-{model}-{pid}"
            lookup[rid] = {"model_id": model, "prompt_id": pid, "sample_idx": 0}
            for judge in judges:
                scores.append(
                    {
                        "response_id": rid,
                        "prompt_id": pid,
                        "judge_model": judge,
                        "judge_model_version": f"{judge}-v1",
                        "scores": _scores(min(5, base + pid)),
                    }
                )
            scores.append(
                {
                    "response_id": rid,
                    "prompt_id": pid,
                    "judge_model": "other_judge",
                    "judge_model_version": None,
                    "scores": _scores(5),
                }
            )
    return scores, lookup


class TestPerPromptFrozenScores:
    """Only frozen judges count, pooled over samples."""

    def test_per_prompt_frozen_scores_ignores_other_judges(self) -> None:
        scores, lookup = _era(1, ("j1", "j2"))
        pp = per_prompt_frozen_scores(scores, lookup, ("j1", "j2"))
        assert pp[(1, "claude", "disclaimer")] == 2.0
        assert (3, "gemini", "disclaimer") in pp

    def test_per_prompt_frozen_scores_skips_nulls(self) -> None:
        scores, lookup = _era(1, ("j1",))
        scores[0]["scores"] = None
        pp = per_prompt_frozen_scores(scores, lookup, ("j1",))
        assert (1, "claude", "disclaimer") not in pp

    def test_per_prompt_frozen_scores_empty_when_no_frozen_judge(self) -> None:
        scores, lookup = _era(1, ("j1",))
        assert per_prompt_frozen_scores(scores, lookup, ("missing",)) == {}


class TestChain:
    """Levels, steps and crisis shifts on a two-era toy chain."""

    def test_compute_steps_sign_follows_later_minus_earlier(self) -> None:
        s_old, l_old = _era(1, ("j1",))
        s_new, l_new = _era(2, ("j1",))
        per_era = {
            "gen4": per_prompt_frozen_scores(s_old, l_old, ("j1",)),
            "gen46": per_prompt_frozen_scores(s_new, l_new, ("j1",)),
            "gen5": per_prompt_frozen_scores(s_new, l_new, ("j1",)),
        }
        steps = compute_steps(per_era, [1, 2, 3])
        cell = steps["gen4->gen46"]["claude"]["disclaimer"]
        assert cell["mean"] == pytest.approx(1.0)
        assert cell["n_paired_prompts"] == 3
        assert steps["gen46->gen5"]["claude"]["disclaimer"]["mean"] == 0.0

    def test_compute_levels_and_crisis(self) -> None:
        s, lk = _era(1, ("j1",))
        per_era = {"gen4": per_prompt_frozen_scores(s, lk, ("j1",))}
        levels = compute_levels(per_era, [1, 2, 3])
        assert levels["gen4"]["claude"]["disclaimer"]["mean"] == pytest.approx(3.0)
        pairs = matched_pairs(PROMPTS)
        assert pairs == [("P01", 1, 2)]
        crisis = compute_crisis_by_era(per_era, pairs)
        assert crisis["gen4"]["claude"]["disclaimer"]["mean"] == pytest.approx(1.0)
        assert crisis["gen4"]["claude"]["disclaimer"]["n_pairs"] == 1

    def test_matched_pairs_ignores_incomplete_pairs(self) -> None:
        prompts = dict(PROMPTS)
        prompts[4] = {
            "id": 4,
            "category": "info_vs_crisis",
            "pair_id": "P02",
            "pair_role": "info",
        }
        assert matched_pairs(prompts) == [("P01", 1, 2)]


class TestComputeBridgeResults:
    """End to end over files, with an in-memory override."""

    def test_compute_bridge_results_reads_files_and_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        (tmp_path / "data").mkdir()
        eras: list[EraSpec] = []
        for name, base in (("gen4", 1), ("gen46", 2), ("gen5", 3)):
            scores, lookup = _era(base, ("j1", "j2"))
            sp = tmp_path / "data" / f"{name}_scores.json"
            lp = tmp_path / "data" / f"{name}_lookup.json"
            sp.write_text(json.dumps(scores))
            lp.write_text(json.dumps(lookup))
            eras.append(EraSpec(name, f"{name} label", sp, lp, ("j1", "j2")))
        results = compute_bridge_results(eras, PROMPTS, generated_at="stamp")
        meta = results["metadata"]
        assert meta["generated_at"] == "stamp"
        assert meta["n_pairs"] == 1
        assert meta["eras"]["gen5"]["judge_model_versions"] == {
            "j1": ["j1-v1"],
            "j2": ["j2-v1"],
        }
        assert meta["eras"]["gen5"]["n_judgments_frozen"] == 18
        assert (
            results["levels"]["gen5"]["claude"]["disclaimer"]["mean"]
            > results["levels"]["gen4"]["claude"]["disclaimer"]["mean"]
        )
        assert set(results["steps"]) == {"gen4->gen46", "gen46->gen5", "gen4->gen5"}
        assert "crisis_shift_changes" in results

        override, _ = _era(1, ("j1", "j2"))
        again = compute_bridge_results(eras, PROMPTS, "stamp", {"gen5": override})
        assert (
            again["levels"]["gen5"]["claude"]["disclaimer"]["mean"]
            == results["levels"]["gen4"]["claude"]["disclaimer"]["mean"]
        )
