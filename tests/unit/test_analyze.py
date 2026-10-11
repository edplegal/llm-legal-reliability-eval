"""Tests for Phase 4: analyze module."""

from __future__ import annotations

from typing import Any

from ai_eval.analyze import (
    bootstrap_ci,
    compute_contextual_calibration,
    compute_judge_responder_matrix,
    compute_model_averages,
    compute_paired_model_diffs,
    compute_pressure_drift,
    compute_self_favoritism,
    compute_variance_components,
    find_critical_failures,
    find_head_to_head_divergence,
    find_high_disagreement,
    flag_self_favoritism,
    get_score_value,
    krippendorff_alpha_ordinal,
    mean,
    median,
    sample_variance,
    std_dev,
)


def _scores_for(score: int) -> dict[str, dict[str, Any]]:
    """Build a scores dict where every applicable dim has the given score."""
    return {
        "disclaimer": {"score": score, "justification": "test"},
        "escalation": {"score": score, "justification": "test"},
        "confidence": {"score": score, "justification": "test"},
        "jurisdiction": {"score": score, "justification": "test"},
        "guardrail": {"score": 0, "justification": "N/A"},
        "regulatory": {"score": 0, "justification": "N/A"},
    }


def _entry(
    rid: str,
    prompt_id: int,
    judge: str,
    responder: str,
    scores: dict[str, dict[str, Any]] | None,
    sample_idx: int = 0,
) -> dict[str, Any]:
    return {
        "response_id": rid,
        "prompt_id": prompt_id,
        "judge_model": judge,
        "responding_model": responder,
        "scores": scores,
        "sample_idx": sample_idx,
    }


class TestMathHelpers:
    """Tests for mean, std_dev, median."""

    def test_mean_normal(self) -> None:
        assert mean([1.0, 2.0, 3.0]) == 2.0

    def test_mean_empty(self) -> None:
        assert mean([]) == 0.0

    def test_mean_cancelling_magnitudes_is_correctly_rounded(self) -> None:
        # Naive float summation, as in builtin sum before 3.12, returns 0.0 here.
        assert mean([1e16, 1.0, -1e16]) == 1.0 / 3.0

    def test_mean_order_of_values_does_not_change_result(self) -> None:
        values = [0.1] * 10 + [1e16, -1e16, 0.7, 0.3]
        assert mean(values) == mean(list(reversed(values)))
        assert mean(values) == mean(sorted(values))

    def test_std_dev_identical(self) -> None:
        assert std_dev([3.0, 3.0, 3.0]) == 0.0

    def test_std_dev_known_values(self) -> None:
        result = std_dev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert abs(result - 2.0) < 0.01

    def test_median_odd(self) -> None:
        assert median([1.0, 3.0, 2.0]) == 2.0

    def test_median_even(self) -> None:
        assert median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_median_empty(self) -> None:
        assert median([]) == 0.0

    def test_sample_variance_known_values(self) -> None:
        assert sample_variance([2.0, 4.0]) == 2.0

    def test_sample_variance_single_value_is_zero(self) -> None:
        assert sample_variance([3.0]) == 0.0


class TestGetScoreValue:
    """Tests for score extraction."""

    def test_normal_score(self) -> None:
        scores: dict[str, Any] = {"disclaimer": {"score": 4, "justification": "Good."}}
        assert get_score_value(scores, "disclaimer") == 4.0

    def test_zero_score_returns_none(self) -> None:
        scores: dict[str, Any] = {"guardrail": {"score": 0, "justification": "N/A"}}
        assert get_score_value(scores, "guardrail") is None

    def test_missing_dimension_returns_none(self) -> None:
        scores: dict[str, Any] = {"disclaimer": {"score": 3, "justification": "OK."}}
        assert get_score_value(scores, "regulatory") is None

    def test_flat_int_read_as_score(self) -> None:
        """A bare numeric dimension (malformed judge output) is tolerated."""
        assert get_score_value({"guardrail": 3}, "guardrail") == 3.0

    def test_flat_zero_is_na(self) -> None:
        assert get_score_value({"guardrail": 0}, "guardrail") is None

    def test_non_dict_non_numeric_returns_none(self) -> None:
        assert get_score_value({"guardrail": "high"}, "guardrail") is None


class TestBootstrapCI:
    """Tests for the percentile bootstrap helper."""

    def test_constant_values_give_tight_ci(self) -> None:
        low, high = bootstrap_ci([3.0, 3.0, 3.0, 3.0])
        assert low == 3.0
        assert high == 3.0

    def test_low_n_returns_degenerate_ci(self) -> None:
        low, high = bootstrap_ci([4.0])
        assert low == 4.0
        assert high == 4.0

    def test_ci_brackets_mean_for_varied_data(self) -> None:
        # Symmetric data, mean = 3
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        low, high = bootstrap_ci(values, iterations=500)
        # Bootstrap CI for the mean should sit around 3 and be valid
        assert low <= 3.0 <= high
        assert low < high

    def test_deterministic_with_seed(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        a = bootstrap_ci(values, iterations=200, seed=42)
        b = bootstrap_ci(values, iterations=200, seed=42)
        assert a == b


class TestKrippendorffAlpha:
    """Tests for ordinal-style Krippendorff α."""

    def test_perfect_agreement_alpha_one(self) -> None:
        # 3 judges, 2 responses, identical scores on every dim
        entries = [
            _entry("R1", 1, j, "modelA", _scores_for(4))
            for j in ("chatgpt", "claude", "gemini")
        ] + [
            _entry("R2", 2, j, "modelA", _scores_for(2))
            for j in ("chatgpt", "claude", "gemini")
        ]
        alphas = krippendorff_alpha_ordinal(entries)
        assert alphas["disclaimer"]["alpha"] == 1.0

    def test_disagreement_lowers_alpha(self) -> None:
        # Wide disagreement across units → α should be near zero or negative
        scored = [
            _entry("R1", 1, "chatgpt", "modelA", _scores_for(1)),
            _entry("R1", 1, "claude", "modelA", _scores_for(5)),
            _entry("R1", 1, "gemini", "modelA", _scores_for(1)),
            _entry("R2", 2, "chatgpt", "modelA", _scores_for(5)),
            _entry("R2", 2, "claude", "modelA", _scores_for(1)),
            _entry("R2", 2, "gemini", "modelA", _scores_for(5)),
        ]
        alphas = krippendorff_alpha_ordinal(scored)
        assert alphas["disclaimer"]["alpha"] < 0.5


class TestComputeModelAverages:
    """Tests for overall model average computation with CIs."""

    def test_returns_mean_ci_n(self) -> None:
        entries: list[dict[str, Any]] = []
        # Two prompts, two judges per response, chatgpt as responder
        for pid in (1, 2):
            for j in ("claude", "gemini"):
                entries.append(
                    _entry(
                        f"R-{pid}",
                        pid,
                        j,
                        "chatgpt",
                        _scores_for(4),
                    )
                )
        result = compute_model_averages(entries)
        stats = result["chatgpt"]["disclaimer"]
        assert stats["mean"] == 4.0
        assert stats["n_prompts"] == 2
        assert stats["n_judgments"] == 4
        # CI for constant data should be degenerate-tight
        assert stats["ci_low"] == 4.0
        assert stats["ci_high"] == 4.0


class TestPairedDiffs:
    """Tests for paired per-prompt model comparison."""

    def test_diff_is_paired_per_prompt(self) -> None:
        entries: list[dict[str, Any]] = []
        # Same prompts (1, 2) answered by both models
        # modelA always scores 4, modelB always scores 2 → diff = +2
        for pid in (1, 2):
            entries.append(_entry(f"R-A{pid}", pid, "judge1", "modelA", _scores_for(4)))
            entries.append(_entry(f"R-B{pid}", pid, "judge1", "modelB", _scores_for(2)))
        diffs = compute_paired_model_diffs(entries)
        key = "modelA__vs__modelB"
        assert diffs[key]["disclaimer"]["mean_diff"] == 2.0
        assert diffs[key]["disclaimer"]["n_paired_prompts"] == 2


class TestFindCriticalFailures:
    """Tests for critical failure detection, including self-judgment exclusion."""

    def test_detects_score_1_from_two_judges(self) -> None:
        entries = [
            _entry("R1", 1, "chatgpt", "claude", _scores_for(1)),
            _entry("R1", 1, "claude", "claude", _scores_for(1)),
            _entry("R1", 1, "gemini", "claude", _scores_for(3)),
        ]
        failures = find_critical_failures(entries)
        # disclaimer scored 1 by 2 judges (chatgpt + claude self)
        disclaimer = [f for f in failures if f["dimension"] == "disclaimer"]
        assert len(disclaimer) == 1
        assert disclaimer[0]["judges_scoring_1"] == 2

    def test_exclude_self_judgment_drops_self_only_failures(self) -> None:
        # claude is responder; only claude (self) and chatgpt score 1.
        entries = [
            _entry("R1", 1, "chatgpt", "claude", _scores_for(1)),
            _entry("R1", 1, "claude", "claude", _scores_for(1)),
            _entry("R1", 1, "gemini", "claude", _scores_for(3)),
        ]
        # Strict: only chatgpt's score-1 counts. n=1 < 2 threshold → no failure.
        strict = find_critical_failures(entries, exclude_self_judgment=True)
        assert not any(f["dimension"] == "disclaimer" for f in strict)

    def test_includes_judge_records(self) -> None:
        entries = [
            _entry("R1", 1, "chatgpt", "modelX", _scores_for(1)),
            _entry("R1", 1, "claude", "modelX", _scores_for(1)),
        ]
        failures = find_critical_failures(entries)
        assert failures
        rec = failures[0]["judge_records"]
        judges = {r["judge_model"] for r in rec}
        assert judges == {"chatgpt", "claude"}

    def test_no_failures_with_high_scores(self) -> None:
        entries = [
            _entry("R-good1", 1, "chatgpt", "claude", _scores_for(4)),
        ]
        assert find_critical_failures(entries) == []


class TestSelfFavoritism:
    """Tests for self-favoritism detection."""

    def test_legacy_diff_metric_still_flags_extreme_bias(self) -> None:
        # chatgpt judges itself 5s and competitor 2s. With no other judges
        # on the same response, the median-of-others premium can't be computed
        # and the legacy diff falls through.
        entries = [
            _entry("R-A", 1, "chatgpt", "chatgpt", _scores_for(5)),
            _entry("R-B", 1, "chatgpt", "claude", _scores_for(2)),
        ]
        fav = compute_self_favoritism(entries)
        flags = flag_self_favoritism(fav, threshold=0.5)
        chatgpt = [f for f in flags if f["judge_model"] == "chatgpt"]
        assert chatgpt
        # The legacy fallback path includes a "diff" alias
        assert chatgpt[0]["diff"] > 0.5

    def test_median_of_others_premium_when_other_judges_present(self) -> None:
        # chatgpt judges its own response 5; claude and gemini both judge it 3.
        # Premium for chatgpt = 5 - median(3, 3) = 2.0 → flagged.
        entries = [
            _entry("R-A", 1, "chatgpt", "chatgpt", _scores_for(5)),
            _entry("R-A", 1, "claude", "chatgpt", _scores_for(3)),
            _entry("R-A", 1, "gemini", "chatgpt", _scores_for(3)),
        ]
        fav = compute_self_favoritism(entries)
        premium = fav["chatgpt"]["disclaimer"]["self_premium_vs_median_of_others"]
        assert abs(premium - 2.0) < 0.01
        flags = flag_self_favoritism(fav, threshold=0.5)
        assert any(
            f["judge_model"] == "chatgpt"
            and f["metric"] == "self_premium_vs_median_of_others"
            for f in flags
        )

    def test_no_bias_when_equal(self) -> None:
        entries = [
            _entry("R-A", 1, "chatgpt", "chatgpt", _scores_for(3)),
            _entry("R-B", 1, "chatgpt", "claude", _scores_for(3)),
        ]
        fav = compute_self_favoritism(entries)
        assert flag_self_favoritism(fav, threshold=0.5) == []

    def test_premium_ci_degenerate_for_single_prompt(self) -> None:
        # One prompt's premium (2.0) → CI collapses to the point estimate.
        entries = [
            _entry("R-A", 1, "chatgpt", "chatgpt", _scores_for(5)),
            _entry("R-A", 1, "claude", "chatgpt", _scores_for(3)),
            _entry("R-A", 1, "gemini", "chatgpt", _scores_for(3)),
        ]
        fav = compute_self_favoritism(entries)
        stats = fav["chatgpt"]["disclaimer"]
        assert stats["premium_ci_low"] == 2.0
        assert stats["premium_ci_high"] == 2.0
        assert stats["n_premium_prompts"] == 1

    def test_premium_ci_zero_when_no_self_judgments(self) -> None:
        entries = [
            _entry("R-B", 1, "chatgpt", "claude", _scores_for(2)),
        ]
        fav = compute_self_favoritism(entries)
        stats = fav["chatgpt"]["disclaimer"]
        assert stats["n_premium_prompts"] == 0
        assert stats["premium_ci_low"] == 0.0
        assert stats["premium_ci_high"] == 0.0


class TestJudgeResponderMatrix:
    """Tests for the 3x3 judge × responder matrix."""

    def test_records_mean_and_n(self) -> None:
        entries = [
            _entry("R1", 1, "chatgpt", "claude", _scores_for(4)),
            _entry("R1", 1, "chatgpt", "claude", _scores_for(2)),
        ]
        matrix = compute_judge_responder_matrix(entries)
        cell = matrix["chatgpt"]["claude"]["disclaimer"]
        assert cell["mean"] == 3.0
        assert cell["n"] == 2


class TestHighDisagreement:
    def test_flags_high_std_dev(self) -> None:
        agreement = {
            "R-test": {
                "disclaimer": {"mean": 3.0, "std_dev": 2.0},
                "escalation": {"mean": 3.0, "std_dev": 0.5},
            }
        }
        flagged = find_high_disagreement(agreement, threshold=1.5)
        assert len(flagged) == 1
        assert flagged[0]["dimension"] == "disclaimer"


class TestHeadToHeadDivergence:
    def test_detects_large_difference(self) -> None:
        entries = [
            _entry("R-A", 1, "gemini", "chatgpt", _scores_for(5)),
            _entry("R-B", 1, "gemini", "claude", _scores_for(1)),
        ]
        div = find_head_to_head_divergence(entries, threshold=2.0)
        assert div
        assert div[0]["difference"] >= 2.0


class TestContextualCalibration:
    """Tests for the headline contextual calibration metric."""

    def test_positive_shift_when_crisis_scored_higher(self) -> None:
        # Pair P01: prompt 1 (info), prompt 2 (crisis).
        # modelA scores 3 on info, 5 on crisis → +2 shift on every dim.
        entries = [
            _entry("R-info", 1, "judge1", "modelA", _scores_for(3)),
            _entry("R-crisis", 2, "judge1", "modelA", _scores_for(5)),
        ]
        prompts_by_id = {
            1: {"id": 1, "pair_id": "P01", "pair_role": "info"},
            2: {"id": 2, "pair_id": "P01", "pair_role": "crisis"},
        }
        result = compute_contextual_calibration(entries, prompts_by_id)
        agg = result["model_aggregate"]["modelA"]["disclaimer"]
        assert agg["mean_shift"] == 2.0
        assert agg["n_pairs"] == 1

    def test_ignores_prompts_without_pair_id(self) -> None:
        entries = [
            _entry("R-X", 99, "judge1", "modelA", _scores_for(4)),
        ]
        prompts_by_id = {
            99: {"id": 99, "pair_id": None, "pair_role": None},
        }
        result = compute_contextual_calibration(entries, prompts_by_id)
        assert result["per_pair"] == []

    def test_skips_pair_without_both_roles(self) -> None:
        entries = [
            _entry("R-info", 1, "judge1", "modelA", _scores_for(3)),
        ]
        prompts_by_id = {
            1: {"id": 1, "pair_id": "P02", "pair_role": "info"},
        }
        result = compute_contextual_calibration(entries, prompts_by_id)
        assert result["per_pair"] == []

    def test_low_n_flag_set_for_single_pair(self) -> None:
        entries = [
            _entry("R-info", 1, "judge1", "modelA", _scores_for(3)),
            _entry("R-crisis", 2, "judge1", "modelA", _scores_for(5)),
        ]
        prompts_by_id = {
            1: {"id": 1, "pair_id": "P01", "pair_role": "info"},
            2: {"id": 2, "pair_id": "P01", "pair_role": "crisis"},
        }
        result = compute_contextual_calibration(entries, prompts_by_id)
        agg = result["model_aggregate"]["modelA"]["disclaimer"]
        assert agg["n_pairs"] == 1
        assert agg["low_n"] is True

    def test_low_n_flag_clear_with_enough_pairs(self) -> None:
        entries: list[dict[str, Any]] = []
        prompts_by_id: dict[int, dict[str, Any]] = {}
        for k in range(3):
            info_id, crisis_id = 10 + 2 * k, 11 + 2 * k
            prompts_by_id[info_id] = {
                "id": info_id,
                "pair_id": f"P0{k}",
                "pair_role": "info",
            }
            prompts_by_id[crisis_id] = {
                "id": crisis_id,
                "pair_id": f"P0{k}",
                "pair_role": "crisis",
            }
            entries.append(
                _entry(f"R-i{k}", info_id, "judge1", "modelA", _scores_for(3))
            )
            entries.append(
                _entry(f"R-c{k}", crisis_id, "judge1", "modelA", _scores_for(4))
            )
        result = compute_contextual_calibration(entries, prompts_by_id)
        agg = result["model_aggregate"]["modelA"]["disclaimer"]
        assert agg["n_pairs"] == 3
        assert agg["low_n"] is False


class TestPressureDrift:
    """Tests for the multi-turn pressure-drift metric."""

    def test_negative_drift_when_rigor_falls(self) -> None:
        # 3-turn sequence: modelA scores 5 at turn_1, 3 at turn_2, 1 at turn_3
        # Drift (T3 - T1) = -4.0
        entries = [
            _entry("R-T1", 1, "judge1", "modelA", _scores_for(5)),
            _entry("R-T2", 2, "judge1", "modelA", _scores_for(3)),
            _entry("R-T3", 3, "judge1", "modelA", _scores_for(1)),
        ]
        prompts_by_id = {
            1: {"id": 1, "pair_id": "S01", "pair_role": "turn_1"},
            2: {"id": 2, "pair_id": "S01", "pair_role": "turn_2"},
            3: {"id": 3, "pair_id": "S01", "pair_role": "turn_3"},
        }
        result = compute_pressure_drift(entries, prompts_by_id)
        agg = result["model_aggregate"]["modelA"]["disclaimer"]
        assert agg["mean_drift"] == -4.0
        assert agg["n_sequences"] == 1

    def test_skips_incomplete_sequences(self) -> None:
        entries = [
            _entry("R-T1", 1, "judge1", "modelA", _scores_for(5)),
            _entry("R-T2", 2, "judge1", "modelA", _scores_for(3)),
        ]
        prompts_by_id = {
            1: {"id": 1, "pair_id": "S02", "pair_role": "turn_1"},
            2: {"id": 2, "pair_id": "S02", "pair_role": "turn_2"},
        }
        result = compute_pressure_drift(entries, prompts_by_id)
        assert result["per_sequence"] == []

    def test_turn_means_and_low_n_exposed(self) -> None:
        # The t3 - t1 metric hides the trajectory; turn_means must carry it,
        # and a single sequence must be marked low_n.
        entries = [
            _entry("R-T1", 1, "judge1", "modelA", _scores_for(5)),
            _entry("R-T2", 2, "judge1", "modelA", _scores_for(3)),
            _entry("R-T3", 3, "judge1", "modelA", _scores_for(1)),
        ]
        prompts_by_id = {
            1: {"id": 1, "pair_id": "S01", "pair_role": "turn_1"},
            2: {"id": 2, "pair_id": "S01", "pair_role": "turn_2"},
            3: {"id": 3, "pair_id": "S01", "pair_role": "turn_3"},
        }
        result = compute_pressure_drift(entries, prompts_by_id)
        agg = result["model_aggregate"]["modelA"]["disclaimer"]
        assert agg["turn_means"] == [5.0, 3.0, 1.0]
        assert agg["low_n"] is True


class TestVarianceComponents:
    """Tests for the prompt/response/judge variance decomposition."""

    def test_decomposes_known_structure(self) -> None:
        # 2 prompts x 2 samples x 2 judges. Judges disagree within every
        # response (var 2), samples are identical within each prompt
        # (response var 0), and the prompts differ (prompt variance).
        entries: list[dict[str, Any]] = []
        for pid, (score_a, score_b) in ((1, (3, 5)), (2, (1, 3))):
            for sample in (0, 1):
                rid = f"R{pid}-{sample}"
                entries.append(
                    _entry(rid, pid, "j1", "modelA", _scores_for(score_a), sample)
                )
                entries.append(
                    _entry(rid, pid, "j2", "modelA", _scores_for(score_b), sample)
                )
        result = compute_variance_components(entries)
        cell = result["per_model_dim"]["modelA"]["disclaimer"]
        assert cell["s2_judge"] == 2.0
        assert cell["s2_response"] == 0.0
        assert cell["s2_prompt"] == 1.5
        assert cell["pct_judge"] == 57.1
        assert cell["n_prompts"] == 2
        assert cell["n_responses"] == 4
        assert cell["n_judgments"] == 8
        # All four applicable dims share the same structure.
        assert result["pooled"]["n_cells"] == 4
        assert result["pooled"]["pct_judge"] == 57.1

    def test_single_sample_marks_insufficient(self) -> None:
        # One sample per prompt: response variance is inseparable from
        # prompt variance, so the cell must be marked, not guessed.
        entries = [
            _entry("R1", 1, "j1", "modelA", _scores_for(3)),
            _entry("R1", 1, "j2", "modelA", _scores_for(5)),
            _entry("R2", 2, "j1", "modelA", _scores_for(2)),
            _entry("R2", 2, "j2", "modelA", _scores_for(4)),
        ]
        result = compute_variance_components(entries)
        cell = result["per_model_dim"]["modelA"]["disclaimer"]
        assert cell.get("insufficient_data") is True
        assert result["pooled"]["n_cells"] == 0

    def test_empty_input_returns_zero_cells(self) -> None:
        result = compute_variance_components([])
        assert result["per_model_dim"] == {}
        assert result["pooled"]["n_cells"] == 0
