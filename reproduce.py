#!/usr/bin/env python3
"""Recompute every released statistic and compare it with the committed files.

Run from a fresh checkout::

    python reproduce.py

The script needs only the standard library and the ``ai_eval`` package in
``src/``; it adds ``src`` to ``sys.path`` itself, so no install step is
required. It writes nothing. Each check recomputes an artifact in memory and
compares it byte for byte with the committed copy, then the numbers-lock check
confirms that every number in ``README.md`` and ``report/post.md`` matches
the recomputed output. The exit status is 0 only when every check passes.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
os.environ["AI_EVAL_BASE_DIR"] = str(ROOT)

from ai_eval import analyze, bridge, numbers_lock, paths, robustness  # noqa: E402


def _committed(path: Path) -> tuple[str, str]:
    """Return a committed artifact's text and its generated_at stamp."""
    text = path.read_text()
    return text, json.loads(text)["metadata"]["generated_at"]


def main() -> int:
    """Run every check and print a one-line verdict per check."""
    results: list[tuple[str, bool, str]] = []
    started = time.time()

    prompts = paths.load_prompt_metadata()
    scores = analyze.load_judge_scores()
    lookup = analyze.load_blind_lookup()

    text, stamp = _committed(ROOT / "data" / "analysis_results.json")
    fresh = analyze.compute_results(scores, lookup, prompts, generated_at=stamp)
    results.append(
        (
            "data/analysis_results.json",
            json.dumps(fresh, indent=2) == text,
            "panel statistics",
        )
    )

    text, stamp = _committed(ROOT / "data" / "bridge_results.json")
    fresh_bridge = bridge.compute_bridge_results(bridge.default_eras(), prompts, stamp)
    results.append(
        (
            "data/bridge_results.json",
            json.dumps(fresh_bridge, indent=2) == text,
            "generational chain under frozen judges",
        )
    )

    text, stamp = _committed(ROOT / "data" / "null_refill_results.json")
    fresh_refill = robustness.compute_null_refill(
        scores,
        lookup,
        prompts,
        stamp,
        bridge_scores=paths.read_json(ROOT / "data" / "bridge_scores.json"),
    )
    results.append(
        (
            "data/null_refill_results.json",
            json.dumps(fresh_refill, indent=2) == text,
            "adversarial null refill",
        )
    )

    arch = ROOT / "data" / "archive" / "gen46"
    text, stamp = _committed(arch / "gen46_analysis_results.json")
    fresh_46 = analyze.compute_results(
        paths.read_json(arch / "gen46_judge_scores.json"),
        paths.read_json(arch / "gen46_blind_lookup.json"),
        prompts,
        generated_at=stamp,
    )
    results.append(
        (
            "data/archive/gen46/gen46_analysis_results.json",
            json.dumps(fresh_46, indent=2) == text,
            "June 2026 run under analyze v4",
        )
    )

    failures = numbers_lock.check_documents(ROOT)
    results.append(
        (
            "numbers lock: README.md and report/post.md",
            not failures,
            f"{numbers_lock.claim_count(ROOT)} claims checked",
        )
    )

    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {detail}")
    for failure in failures:
        print(f"      {failure}")
    elapsed = time.time() - started
    all_ok = all(ok for _, ok, _ in results)
    print(f"\n{'All checks passed' if all_ok else 'CHECKS FAILED'} in {elapsed:.1f} s.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
