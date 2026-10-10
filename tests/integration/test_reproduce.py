"""The release reproduces: every committed artifact and every reported number.

These tests run against the repository's own data, not fixtures. They are
what ``python reproduce.py`` runs, exposed to pytest so that CI fails when a
number in the README or the report drifts from the analysis output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import reproduce  # noqa: E402
from ai_eval import analyze, numbers_lock, paths  # noqa: E402


@pytest.fixture(autouse=True)
def _release_base_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_EVAL_BASE_DIR", str(ROOT))


def test_numbers_lock_readme_and_report_match_analysis_output() -> None:
    failures = numbers_lock.check_documents(ROOT)
    assert failures == [], "\n".join(failures)
    assert numbers_lock.claim_count(ROOT) > 50


def test_analysis_results_are_byte_identical() -> None:
    committed = (ROOT / "data" / "analysis_results.json").read_text()
    stamp = json.loads(committed)["metadata"]["generated_at"]
    fresh = analyze.compute_results(
        analyze.load_judge_scores(),
        analyze.load_blind_lookup(),
        paths.load_prompt_metadata(),
        generated_at=stamp,
    )
    assert json.dumps(fresh, indent=2) == committed


def test_reproduce_script_passes_every_check(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert reproduce.main() == 0
    out = capsys.readouterr().out
    assert "FAIL" not in out
    assert "All checks passed" in out
