"""Generational chain under frozen judges (the post's Finding 5).

Three judged runs share the same sixty prompts: the spring 2026 run (Sonnet 4,
GPT-4o, Gemini 2.5 Flash), the June 2026 run in which only the Claude arm
changed (Sonnet 4.6), and the current six-model run. Two judges were held
fixed across all three: ``gpt-4o-2024-08-06`` and ``gemini-2.5-flash`` at
temperature 0.0. Scoring every run with only those two judges makes the
comparison judge-controlled: a shift can then be attributed to the responding
model rather than to the grader.

The statistics mirror :mod:`ai_eval.analyze`: one mean per (prompt, model,
dimension) over all judgments of the frozen judges, paired differences over
the sixty prompts, crisis shifts over the fifteen matched pairs, and the same
seeded percentile bootstrap.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ai_eval.analyze import (
    BOOTSTRAP_ITERATIONS,
    BOOTSTRAP_SEED,
    bootstrap_ci,
    get_score_value,
    mean,
)
from ai_eval.paths import (
    archive_dir,
    data_dir,
    generated_at_stamp,
    load_prompt_metadata,
    read_json,
    write_json_with_rotation,
)
from ai_eval.schema import APPLICABLE_DIMENSIONS

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

BRIDGE_VERSION = 1

PerPromptScores = dict[tuple[int, str, str], float]


@dataclass(frozen=True)
class EraSpec:
    """One judged run and the judge ids within it that were held frozen."""

    name: str
    label: str
    judge_scores: Path
    blind_lookup: Path
    frozen_judges: tuple[str, ...]


def default_eras() -> list[EraSpec]:
    """The three eras in chronological order, resolved against the data dir."""
    arch = archive_dir()
    return [
        EraSpec(
            name="gen4",
            label="spring 2026 run: Sonnet 4, GPT-4o, Gemini 2.5 Flash",
            judge_scores=arch / "gen4" / "gen4_judge_scores.json",
            blind_lookup=arch / "gen4" / "gen4_blind_lookup.json",
            frozen_judges=("chatgpt", "gemini"),
        ),
        EraSpec(
            name="gen46",
            label="June 2026 run: Sonnet 4.6, GPT-4o, Gemini 2.5 Flash",
            judge_scores=arch / "gen46" / "gen46_judge_scores.json",
            blind_lookup=arch / "gen46" / "gen46_blind_lookup.json",
            frozen_judges=("chatgpt", "gemini"),
        ),
        EraSpec(
            name="gen5",
            label="July 2026 run, bridge pass: six gen-5 models, frozen judges",
            judge_scores=data_dir() / "bridge_scores.json",
            blind_lookup=data_dir() / "blind_lookup.json",
            frozen_judges=("bridge_gpt4o", "bridge_gemini25"),
        ),
    ]


# Responder ids that exist in every era. In the archived runs "claude" is
# Sonnet 4 then Sonnet 4.6; in gen 5 it is Sonnet 5. "chatgpt" is GPT-4o then
# GPT-5.5; "gemini" is Gemini 2.5 Flash then 3.5 Flash.
CHAIN_MODELS: tuple[str, ...] = ("claude", "chatgpt", "gemini")
STEPS: tuple[tuple[str, str], ...] = (
    ("gen4", "gen46"),
    ("gen46", "gen5"),
    ("gen4", "gen5"),
)


def per_prompt_frozen_scores(
    scores: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
    frozen_judges: tuple[str, ...],
) -> PerPromptScores:
    """Mean score per (prompt, responding model, dim) over the frozen judges.

    Every judgment by a frozen judge counts once, so samples and judges are
    pooled exactly as :func:`ai_eval.analyze._per_prompt_model_dim_score`
    pools them.
    """
    buckets: dict[tuple[int, str, str], list[float]] = defaultdict(list)
    judges = set(frozen_judges)
    for record in scores:
        if record["scores"] is None or record["judge_model"] not in judges:
            continue
        entry = lookup[record["response_id"]]
        for dim in APPLICABLE_DIMENSIONS:
            val = get_score_value(record["scores"], dim)
            if val is not None:
                buckets[(entry["prompt_id"], entry["model_id"], dim)].append(val)
    return {key: mean(vals) for key, vals in buckets.items() if vals}


def _ci_record(values: list[float], n_key: str) -> dict[str, Any]:
    lo, hi = bootstrap_ci(values)
    return {
        "mean": round(mean(values), 3),
        "ci_low": round(lo, 3),
        "ci_high": round(hi, 3),
        n_key: len(values),
    }


def compute_levels(
    per_era: dict[str, PerPromptScores], prompt_ids: list[int]
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Mean of per-prompt means per era, model, dim, with a prompt bootstrap."""
    out: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for era, pp in per_era.items():
        out[era] = {}
        for model in CHAIN_MODELS:
            out[era][model] = {}
            for dim in APPLICABLE_DIMENSIONS:
                vals = [
                    pp[(pid, model, dim)]
                    for pid in prompt_ids
                    if (pid, model, dim) in pp
                ]
                if vals:
                    out[era][model][dim] = _ci_record(vals, "n_prompts")
    return out


def compute_steps(
    per_era: dict[str, PerPromptScores], prompt_ids: list[int]
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Paired per-prompt differences (later era minus earlier) for each step."""
    out: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for old, new in STEPS:
        key = f"{old}->{new}"
        out[key] = {}
        for model in CHAIN_MODELS:
            out[key][model] = {}
            for dim in APPLICABLE_DIMENSIONS:
                diffs = [
                    per_era[new][(pid, model, dim)] - per_era[old][(pid, model, dim)]
                    for pid in prompt_ids
                    if (pid, model, dim) in per_era[new]
                    and (pid, model, dim) in per_era[old]
                ]
                if diffs:
                    out[key][model][dim] = _ci_record(diffs, "n_paired_prompts")
    return out


def matched_pairs(
    prompts_by_id: dict[int, dict[str, Any]],
) -> list[tuple[str, int, int]]:
    """(pair_id, info prompt, crisis prompt) for every complete matched pair."""
    pairs: dict[str, dict[str, int]] = defaultdict(dict)
    for pid, info in prompts_by_id.items():
        pair_id = info.get("pair_id")
        role = info.get("pair_role")
        if pair_id and role in ("info", "crisis"):
            pairs[pair_id][role] = pid
    return [
        (pair_id, roles["info"], roles["crisis"])
        for pair_id, roles in sorted(pairs.items())
        if "info" in roles and "crisis" in roles
    ]


def _pair_shifts(
    pp: PerPromptScores, pairs: list[tuple[str, int, int]], model: str, dim: str
) -> list[float]:
    return [
        pp[(crisis, model, dim)] - pp[(info, model, dim)]
        for _, info, crisis in pairs
        if (info, model, dim) in pp and (crisis, model, dim) in pp
    ]


def compute_crisis_by_era(
    per_era: dict[str, PerPromptScores], pairs: list[tuple[str, int, int]]
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Crisis minus calm shift per era, model, dim, bootstrapped over pairs."""
    out: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for era, pp in per_era.items():
        out[era] = {}
        for model in CHAIN_MODELS:
            out[era][model] = {}
            for dim in APPLICABLE_DIMENSIONS:
                shifts = _pair_shifts(pp, pairs, model, dim)
                if shifts:
                    out[era][model][dim] = _ci_record(shifts, "n_pairs")
    return out


def compute_crisis_shift_changes(
    per_era: dict[str, PerPromptScores], pairs: list[tuple[str, int, int]]
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Change in the per-pair crisis shift between eras, paired over pairs."""
    out: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for old, new in STEPS:
        key = f"{old}->{new}"
        out[key] = {}
        for model in CHAIN_MODELS:
            out[key][model] = {}
            for dim in APPLICABLE_DIMENSIONS:
                changes = [
                    (per_era[new][(c, model, dim)] - per_era[new][(i, model, dim)])
                    - (per_era[old][(c, model, dim)] - per_era[old][(i, model, dim)])
                    for _, i, c in pairs
                    if all(
                        (p, model, dim) in per_era[e]
                        for p in (i, c)
                        for e in (old, new)
                    )
                ]
                if changes:
                    out[key][model][dim] = _ci_record(changes, "n_pairs")
    return out


def era_metadata(spec: EraSpec, scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts and served judge versions for one era, frozen judges only."""
    frozen = [s for s in scores if s["judge_model"] in spec.frozen_judges]
    versions: dict[str, set[str]] = defaultdict(set)
    for s in frozen:
        ver = s.get("judge_model_version")
        if ver:
            versions[s["judge_model"]].add(str(ver))
    return {
        "label": spec.label,
        "judge_scores": str(spec.judge_scores.relative_to(data_dir().parent)),
        "blind_lookup": str(spec.blind_lookup.relative_to(data_dir().parent)),
        "frozen_judges": list(spec.frozen_judges),
        "judge_model_versions": {k: sorted(v) for k, v in versions.items()},
        "n_judgments_frozen": len(frozen),
        "n_judgments_null": sum(1 for s in frozen if s["scores"] is None),
    }


def compute_bridge_results(
    eras: list[EraSpec],
    prompts_by_id: dict[int, dict[str, Any]],
    generated_at: str | None = None,
    score_overrides: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Load every era and compute the generational chain in memory.

    ``score_overrides`` maps an era name to judge scores to use in place of
    the era's file; the robustness module uses it to refill the bridge nulls.
    """
    per_era: dict[str, PerPromptScores] = {}
    meta_eras: dict[str, dict[str, Any]] = {}
    overrides = score_overrides or {}
    for spec in eras:
        scores: list[dict[str, Any]] = overrides.get(spec.name) or read_json(
            spec.judge_scores
        )
        lookup: dict[str, dict[str, Any]] = read_json(spec.blind_lookup)
        per_era[spec.name] = per_prompt_frozen_scores(
            scores, lookup, spec.frozen_judges
        )
        meta_eras[spec.name] = era_metadata(spec, scores)
    prompt_ids = sorted(prompts_by_id)
    pairs = matched_pairs(prompts_by_id)
    return {
        "metadata": {
            "bridge_version": BRIDGE_VERSION,
            "generated_at": generated_at or generated_at_stamp(),
            "n_prompts": len(prompt_ids),
            "n_pairs": len(pairs),
            "chain_models": list(CHAIN_MODELS),
            "eras": meta_eras,
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "levels": compute_levels(per_era, prompt_ids),
        "steps": compute_steps(per_era, prompt_ids),
        "crisis_by_era": compute_crisis_by_era(per_era, pairs),
        "crisis_shift_changes": compute_crisis_shift_changes(per_era, pairs),
    }


def run_bridge() -> None:
    """Compute the chain and write ``data/bridge_results.json`` with rotation."""
    results = compute_bridge_results(default_eras(), load_prompt_metadata())
    output_path = data_dir() / "bridge_results.json"
    write_json_with_rotation(output_path, results)
    logger.info("Bridge results saved to %s", output_path)
    print_summary(results)


def print_summary(results: dict[str, Any]) -> None:
    """Print the Claude disclaimer chain and the crisis table to stdout."""
    print("\n--- LEVELS UNDER FROZEN JUDGES (disclaimer) ---")
    for model in CHAIN_MODELS:
        chain = " -> ".join(
            f"{results['levels'][era][model]['disclaimer']['mean']:.2f}"
            for era in results["levels"]
        )
        print(f"  {model:<8} {chain}")
    print("\n--- CRISIS-DISCLAIMER SHIFT BY ERA ---")
    for model in CHAIN_MODELS:
        cells = []
        for era in results["crisis_by_era"]:
            c = results["crisis_by_era"][era][model]["disclaimer"]
            cells.append(f"{c['mean']:+.2f} [{c['ci_low']:+.2f}, {c['ci_high']:+.2f}]")
        print(f"  {model:<8} " + " | ".join(cells))


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    run_bridge()


if __name__ == "__main__":
    main()
