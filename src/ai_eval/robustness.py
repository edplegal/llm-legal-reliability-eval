"""Adversarial null refill: how much can the unparseable grades move the results?

Twenty-five of the 6,480 panel grades came back as unparseable JSON and were
excluded. This module refills every null with the worst case (all 1s) and the
best case (all 5s), reruns the full analysis in memory, and reports the largest
change in each family of statistics the post reports, together with any cell
whose confidence interval changes sides of zero and any model ranking that
flips. A dimension is refilled only when a majority of the other judges scored
it on the same answer; otherwise it stays not-applicable, matching how the
judges treated the guardrail and regulatory dimensions.
"""

from __future__ import annotations

import copy
import logging
from collections import defaultdict
from typing import Any

from ai_eval.analyze import (
    compute_results,
    get_score_value,
    load_blind_lookup,
    load_judge_scores,
)
from ai_eval.bridge import EraSpec, compute_bridge_results, default_eras
from ai_eval.paths import (
    data_dir,
    generated_at_stamp,
    load_prompt_metadata,
    read_json,
    write_json_with_rotation,
)
from ai_eval.schema import APPLICABLE_DIMENSIONS, DIMENSIONS

logger = logging.getLogger(__name__)

ROBUSTNESS_VERSION = 1
FILLS: tuple[int, ...] = (1, 5)

Family = dict[str, float]
Interval = dict[str, tuple[float, float]]


def applicable_dimensions(
    scores: list[dict[str, Any]],
) -> dict[str, set[str]]:
    """Dimensions scored (non-N/A) by a majority of judges, per response."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    judged: dict[str, int] = defaultdict(int)
    for record in scores:
        if record["scores"] is None:
            continue
        rid = record["response_id"]
        judged[rid] += 1
        for dim in DIMENSIONS:
            if get_score_value(record["scores"], dim) is not None:
                counts[rid][dim] += 1
    return {
        rid: {dim for dim in DIMENSIONS if counts[rid][dim] * 2 > judged[rid]}
        for rid in judged
    }


def refill_nulls(scores: list[dict[str, Any]], fill: int) -> list[dict[str, Any]]:
    """Return a deep copy with every null judgment replaced by ``fill``."""
    applicable = applicable_dimensions(scores)
    refilled = copy.deepcopy(scores)
    for record in refilled:
        if record["scores"] is not None:
            continue
        dims = applicable.get(record["response_id"], set(APPLICABLE_DIMENSIONS))
        record["scores"] = {
            dim: {"score": fill if dim in dims else 0, "justification": "refilled"}
            for dim in DIMENSIONS
        }
    return refilled


def reported_numbers(results: dict[str, Any]) -> tuple[dict[str, Family], Interval]:
    """The point estimates the post reports, grouped by family, plus intervals."""
    fam: dict[str, Family] = defaultdict(dict)
    ci: Interval = {}
    for judge, dims in results["self_favoritism"].items():
        for dim in APPLICABLE_DIMENSIONS:
            c = dims[dim]
            fam["style"][f"{judge}/{dim}"] = c["style_deviation"]
            fam["net"][f"{judge}/{dim}"] = c["net_self_premium"]
            ci[f"style/{judge}/{dim}"] = (c["style_ci_low"], c["style_ci_high"])
            ci[f"net/{judge}/{dim}"] = (c["net_ci_low"], c["net_ci_high"])
    for model, dims in results["contextual_calibration"]["model_aggregate"].items():
        for dim in ("disclaimer", "escalation"):
            c = dims[dim]
            fam["crisis"][f"{model}/{dim}"] = c["mean_shift"]
            ci[f"crisis/{model}/{dim}"] = (c["ci_low"], c["ci_high"])
    for model, dims in results["pressure_drift"]["model_aggregate"].items():
        c = dims["confidence"]
        fam["confidence_drift"][model] = c["mean_drift"]
        ci[f"confidence_drift/{model}"] = (c["ci_low"], c["ci_high"])
        for i, t in enumerate(dims["disclaimer"]["turn_means"]):
            if t is not None:
                fam["disclaimer_turn_means"][f"{model}/turn_{i + 1}"] = t
    for model, dims in results["model_averages"].items():
        fam["disclaimer_means"][model] = dims["disclaimer"]["mean"]
    for dim, stats in results["krippendorff_alpha"].items():
        fam["alpha"][dim] = stats["alpha"]
    pooled = results["variance_components"]["pooled"]
    for key in ("pct_prompt", "pct_response", "pct_judge"):
        fam["variance_pct"][key] = pooled[key]
    return dict(fam), ci


def _excludes_zero(interval: tuple[float, float]) -> bool:
    return interval[0] > 0 or interval[1] < 0


def compare(base: dict[str, Any], alt: dict[str, Any]) -> dict[str, Any]:
    """Largest change per family, significance flips, and ranking flips."""
    fb, cb = reported_numbers(base)
    fa, ca = reported_numbers(alt)
    families: dict[str, dict[str, Any]] = {}
    for name, values in fb.items():
        worst = max(values, key=lambda k: abs(fa[name][k] - values[k]))
        families[name] = {
            "max_abs_change": round(abs(fa[name][worst] - values[worst]), 3),
            "at": worst,
            "before": values[worst],
            "after": fa[name][worst],
        }
    flips = []
    for key in cb:
        if _excludes_zero(cb[key]) == _excludes_zero(ca[key]):
            continue
        family, _, cell = key.partition("/")
        flips.append(
            {
                "cell": key,
                "before_value": fb[family][cell],
                "after_value": fa[family][cell],
                "before_ci": list(cb[key]),
                "after_ci": list(ca[key]),
            }
        )
    ranking_flips: list[str] = []
    for dim in APPLICABLE_DIMENSIONS:
        order_b = sorted(
            base["model_averages"], key=lambda m: base["model_averages"][m][dim]["mean"]
        )
        order_a = sorted(
            alt["model_averages"], key=lambda m: alt["model_averages"][m][dim]["mean"]
        )
        if order_b != order_a:
            ranking_flips.append(dim)
    return {
        "families": families,
        "significance_flips": flips,
        "core_dimension_ranking_flips": ranking_flips,
        "n_critical_failures": len(alt["critical_failures"]),
        "n_high_disagreement": len(alt["high_disagreement"]),
    }


def bridge_numbers(results: dict[str, Any]) -> tuple[Family, Interval]:
    """Finding 5 numbers that depend on the bridge pass (the gen-5 era)."""
    fam: Family = {}
    ci: Interval = {}
    for model, dims in results["levels"]["gen5"].items():
        for dim, c in dims.items():
            fam[f"level/{model}/{dim}"] = c["mean"]
    for model, dims in results["crisis_by_era"]["gen5"].items():
        for dim, c in dims.items():
            fam[f"crisis/{model}/{dim}"] = c["mean"]
            ci[f"crisis/{model}/{dim}"] = (c["ci_low"], c["ci_high"])
    for step, models in results["steps"].items():
        if not step.endswith("gen5"):
            continue
        for model, dims in models.items():
            for dim, c in dims.items():
                fam[f"step/{step}/{model}/{dim}"] = c["mean"]
                ci[f"step/{step}/{model}/{dim}"] = (c["ci_low"], c["ci_high"])
    return fam, ci


def compare_bridge(base: dict[str, Any], alt: dict[str, Any]) -> dict[str, Any]:
    """Largest change and significance flips among the bridge-dependent numbers."""
    fb, cb = bridge_numbers(base)
    fa, ca = bridge_numbers(alt)
    worst = max(fb, key=lambda k: abs(fa[k] - fb[k]))
    return {
        "max_abs_change": round(abs(fa[worst] - fb[worst]), 3),
        "at": worst,
        "before": fb[worst],
        "after": fa[worst],
        "significance_flips": [
            {"cell": k, "before_ci": list(cb[k]), "after_ci": list(ca[k])}
            for k in cb
            if _excludes_zero(cb[k]) != _excludes_zero(ca[k])
        ],
    }


def _count_by_judge(nulls: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for s in nulls:
        counts[s["judge_model"]] += 1
    return dict(counts)


def compute_null_refill(
    scores: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
    prompts_by_id: dict[int, dict[str, Any]],
    generated_at: str | None = None,
    bridge_scores: list[dict[str, Any]] | None = None,
    eras: list[EraSpec] | None = None,
) -> dict[str, Any]:
    """Run the base analysis and one refilled analysis per fill value.

    When ``bridge_scores`` is given, the bridge pass's own nulls are refilled
    the same way and the gen-5 Finding 5 numbers are compared too.
    """
    base = compute_results(scores, lookup, prompts_by_id, generated_at="n/a")
    nulls = [s for s in scores if s["scores"] is None]
    bridge_nulls = [s for s in bridge_scores or [] if s["scores"] is None]
    base_bridge: dict[str, Any] | None = None
    if bridge_scores is not None:
        base_bridge = compute_bridge_results(
            eras or default_eras(), prompts_by_id, "n/a", {"gen5": bridge_scores}
        )
    fills: dict[str, dict[str, Any]] = {}
    for fill in FILLS:
        refilled = compute_results(
            refill_nulls(scores, fill), lookup, prompts_by_id, "n/a"
        )
        entry = compare(base, refilled)
        if bridge_scores is not None and base_bridge is not None:
            alt_bridge = compute_bridge_results(
                eras or default_eras(),
                prompts_by_id,
                "n/a",
                {"gen5": refill_nulls(bridge_scores, fill)},
            )
            entry["bridge"] = compare_bridge(base_bridge, alt_bridge)
        fills[f"fill_{fill}"] = entry
    return {
        "metadata": {
            "robustness_version": ROBUSTNESS_VERSION,
            "generated_at": generated_at or generated_at_stamp(),
            "n_judgments_total": len(scores),
            "n_nulls_refilled": len(nulls),
            "null_judgments_by_judge": _count_by_judge(nulls),
            "n_bridge_judgments_total": len(bridge_scores or []),
            "n_bridge_nulls_refilled": len(bridge_nulls),
            "bridge_null_judgments_by_judge": _count_by_judge(bridge_nulls),
            "fills": list(FILLS),
            "base_n_critical_failures": len(base["critical_failures"]),
            "base_n_high_disagreement": len(base["high_disagreement"]),
        },
        "refills": fills,
    }


def print_summary(results: dict[str, Any]) -> None:
    """Print the largest change per family for each fill."""
    for fill, comp in results["refills"].items():
        print(f"\n--- NULL REFILL {fill}: largest change per family ---")
        for name, rec in comp["families"].items():
            print(f"  {name:<22} {rec['max_abs_change']:.3f} at {rec['at']}")
        print(
            f"  significance flips: {[f['cell'] for f in comp['significance_flips']]}"
        )
        print(f"  ranking flips: {comp['core_dimension_ranking_flips']}")
        if "bridge" in comp:
            b = comp["bridge"]
            flipped = [f["cell"] for f in b["significance_flips"]]
            print(
                f"  bridge (Finding 5, gen 5): {b['max_abs_change']:.3f} "
                f"at {b['at']}; flips {flipped}"
            )


def run_null_refill() -> None:
    """Compute and write ``data/null_refill_results.json`` with rotation."""
    results = compute_null_refill(
        load_judge_scores(),
        load_blind_lookup(),
        load_prompt_metadata(),
        bridge_scores=read_json(data_dir() / "bridge_scores.json"),
    )
    output_path = data_dir() / "null_refill_results.json"
    write_json_with_rotation(output_path, results)
    logger.info("Null-refill results saved to %s", output_path)
    print_summary(results)


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    run_null_refill()


if __name__ == "__main__":
    main()
