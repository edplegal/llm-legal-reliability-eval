"""Generate an interactive HTML report from pipeline analysis results."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

DIMENSIONS = [
    "disclaimer",
    "escalation",
    "confidence",
    "jurisdiction",
    "guardrail",
    "regulatory",
]

DIMENSION_NA_NOTE = {
    "guardrail": "Applies only to adversarial_pressure prompts.",
    "regulatory": "Applies only to prompts about AI deployed in regulated domains.",
}


def load_json(filename: str) -> Any:
    """Load a JSON file from the data directory."""
    path = DATA_DIR / filename
    with path.open() as f:
        return json.load(f)


def esc(text: Any) -> str:
    """HTML-escape a value."""
    return html.escape(str(text))


def score_color(score: float) -> str:
    """Return a CSS color for a 1-5 score using fixed, documented bins."""
    if score == 0:
        return "#999"
    if score < 2.0:
        return "#e74c3c"  # red: critical
    if score < 3.0:
        return "#e67e22"  # orange: poor
    if score < 3.5:
        return "#f1c40f"  # yellow: mediocre
    if score < 4.5:
        return "#27ae60"  # green: good
    return "#2ecc71"  # bright green: excellent


def score_badge_with_ci(
    mean_val: float,
    ci_low: float,
    ci_high: float,
    n_prompts: int,
    n_judgments: int,
) -> str:
    """Render a score badge with CI and sample size in tooltip + sub-line."""
    if n_prompts == 0:
        return '<span class="badge na">N/A</span>'
    color = score_color(mean_val)
    title = (
        f"mean={mean_val:.2f}, 95% CI=[{ci_low:.2f}, {ci_high:.2f}], "
        f"n_prompts={n_prompts}, n_judgments={n_judgments}"
    )
    return (
        f'<span class="badge" style="background:{color}" title="{esc(title)}">'
        f"{mean_val:.2f}</span>"
        f'<div class="badge-ci">[{ci_low:.2f}, {ci_high:.2f}]</div>'
        f'<div class="badge-n">n={n_prompts}</div>'
    )


def simple_badge(score: float, n: int | None = None) -> str:
    """Render a score badge without CI (for matrix cells, category rows)."""
    if score == 0 and (n is None or n == 0):
        return '<span class="badge na">N/A</span>'
    color = score_color(score)
    suffix = f'<div class="badge-n">n={n}</div>' if n is not None else ""
    return (
        f'<span class="badge" style="background:{color}">{score:.1f}</span>'
        f"{suffix}"
    )


def get_git_sha() -> str:
    """Best-effort git SHA capture; returns 'untracked' on failure."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(BASE_DIR),
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode().strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "untracked"


def detect_prompts_data_mismatch(
    raw_responses: list[dict[str, Any]],
) -> str | None:
    """Return a warning string if raw_responses were collected against a
    different version of prompts.json than the one currently on disk.

    Uses the prompts_hash that collect.py stamps on every entry. Old data
    collected before this field existed (or against a different prompts
    file) is flagged so the reader knows the contextual-calibration and
    pressure-drift sections may show the framework but not real signal.
    """
    if not raw_responses:
        return None
    prompts_path = BASE_DIR / "prompts.json"
    if not prompts_path.exists():
        return None
    with prompts_path.open("rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()[:12]

    stamps = {r.get("prompts_hash") for r in raw_responses}
    if stamps == {None}:
        return (
            "Existing responses were collected before prompt-version "
            "stamping was added. The Contextual Calibration and Pressure "
            "Drift sections show the framework operating, but their "
            "numeric values cannot be interpreted because the responses "
            "may not align with the current prompts.json. Re-run "
            "`python -m ai_eval.collect` and `python -m ai_eval.judge` "
            "against the current prompts.json for valid metrics."
        )
    if current_hash not in stamps:
        return (
            f"Responses were collected against a different prompts.json "
            f"(stamp(s): {sorted(s for s in stamps if s)}) than the current "
            f"file (stamp: {current_hash}). Contextual Calibration and "
            f"Pressure Drift values reflect a stale alignment. Re-run "
            f"collect.py + judge.py against the current prompts.json."
        )
    return None


def build_data_warning(warning: str | None) -> str:
    """Render a prominent warning banner if the data is misaligned."""
    if not warning:
        return ""
    return f"""
    <section style="background:#5a2a2a; border-left:4px solid #e74c3c;">
    <h2 style="color:#ffb3b3">⚠ Data Provenance Warning</h2>
    <p>{esc(warning)}</p>
    </section>
    """


def build_header(meta: dict[str, Any]) -> str:
    """Header with run metadata for reproducibility."""
    generated = meta.get("generated_at", datetime.now(UTC).isoformat())
    n_prompts = meta.get("n_prompts", 0)
    n_models = meta.get("n_responder_models", 0)
    n_judges = meta.get("n_judge_models", 0)
    n_samples = meta.get("n_samples_per_cell", 1)
    n_total = meta.get("n_judgments_total", 0)
    n_valid = meta.get("n_judgments_valid", 0)
    n_null = meta.get("n_judgments_null", 0)
    sha = get_git_sha()
    judge_versions = meta.get("judge_model_versions", {})
    version_lines = ""
    if judge_versions:
        rows = "".join(
            f"<li><strong>{esc(j)}:</strong> {esc(', '.join(versions))}</li>"
            for j, versions in sorted(judge_versions.items())
        )
        version_lines = f"<ul class='meta-list'>{rows}</ul>"
    return f"""
<h1>AI Safety Evaluation Report
<small>
Blinded Cross-Model Legal/Regulatory Assessment &mdash;
{n_prompts} prompts &times; {n_models} models &times; {n_judges} judges
&times; {n_samples} sample(s) per cell<br>
Judgments: {n_valid} valid / {n_total} total ({n_null} null) &middot;
Generated {esc(generated)} &middot;
Repo {esc(sha)}
</small></h1>
{version_lines}
"""


def build_model_averages_section(analysis: dict[str, Any]) -> str:
    """Overall model averages with bootstrap CIs and n_prompts."""
    avgs: dict[str, dict[str, dict[str, float]]] = analysis["model_averages"]
    rows = ""
    for model_id in sorted(avgs.keys()):
        dims = avgs[model_id]
        cells = ""
        for d in DIMENSIONS:
            stats = dims.get(d, {})
            cells += "<td>" + score_badge_with_ci(
                float(stats.get("mean", 0.0)),
                float(stats.get("ci_low", 0.0)),
                float(stats.get("ci_high", 0.0)),
                int(stats.get("n_prompts", 0)),
                int(stats.get("n_judgments", 0)),
            ) + "</td>"
        rows += f"<tr><td><strong>{esc(model_id)}</strong></td>{cells}</tr>\n"
    headers = "".join(f"<th>{esc(d)}</th>" for d in DIMENSIONS)
    na_notes = "".join(
        f"<li><strong>{esc(dim)}:</strong> {esc(note)}</li>"
        for dim, note in DIMENSION_NA_NOTE.items()
    )
    return f"""
    <section id="model-averages">
    <h2>Overall Model Averages</h2>
    <p class="caption">Cells show <strong>mean</strong>, [95% bootstrap CI],
    and <em>n</em> (number of prompts contributing). The bootstrap resamples
    prompts, so guardrail and regulatory CIs reflect their smaller applicable
    prompt counts.</p>
    <table>
    <thead><tr><th>Model</th>{headers}</tr></thead>
    <tbody>{rows}</tbody>
    </table>
    <details><summary>Dimension applicability notes</summary>
    <ul class="meta-list">{na_notes}</ul></details>
    </section>
    """


def build_paired_diffs_section(analysis: dict[str, Any]) -> str:
    """Paired per-prompt model-vs-model differences with bootstrap CIs."""
    paired: dict[str, dict[str, dict[str, float]]] = analysis.get(
        "paired_model_diffs", {}
    )
    if not paired:
        return ""
    rows = ""
    for key in sorted(paired.keys()):
        dims = paired[key]
        cells = ""
        for d in DIMENSIONS:
            stats = dims.get(d, {})
            n = int(stats.get("n_paired_prompts", 0))
            if n == 0:
                cells += '<td><span class="badge na">N/A</span></td>'
                continue
            m_diff = float(stats.get("mean_diff", 0.0))
            ci_low = float(stats.get("ci_low", 0.0))
            ci_high = float(stats.get("ci_high", 0.0))
            crosses_zero = ci_low <= 0 <= ci_high
            color = "#7f8c8d" if crosses_zero else (
                "#27ae60" if m_diff > 0 else "#e74c3c"
            )
            sign = "+" if m_diff >= 0 else ""
            title = (
                f"diff={m_diff:.3f}, 95% CI=[{ci_low:.3f}, {ci_high:.3f}], "
                f"n_paired_prompts={n}"
                + (" (CI crosses zero)" if crosses_zero else "")
            )
            cells += (
                f'<td><span class="badge" style="background:{color}"'
                f' title="{esc(title)}">{sign}{m_diff:.2f}</span>'
                f'<div class="badge-ci">[{ci_low:.2f}, {ci_high:.2f}]</div>'
                f'<div class="badge-n">n={n}</div></td>'
            )
        rows += f"<tr><td><strong>{esc(key)}</strong></td>{cells}</tr>\n"
    headers = "".join(f"<th>{esc(d)}</th>" for d in DIMENSIONS)
    return f"""
    <section id="paired-diffs">
    <h2>Paired Model Differences</h2>
    <p class="caption">For each prompt, the per-prompt mean of model A minus
    model B (averaged across judges/samples), bootstrapped over prompts.
    <strong>Gray</strong> = 95% CI crosses zero (not distinguishable from no
    difference at this sample size).</p>
    <table>
    <thead><tr><th>Comparison</th>{headers}</tr></thead>
    <tbody>{rows}</tbody>
    </table>
    </section>
    """


def build_krippendorff_section(analysis: dict[str, Any]) -> str:
    """Inter-judge agreement (Krippendorff α, ordinal)."""
    alphas: dict[str, dict[str, float]] = analysis.get("krippendorff_alpha", {})
    if not alphas:
        return ""
    rows = ""
    for dim in DIMENSIONS:
        stats = alphas.get(dim, {})
        n_units = int(stats.get("n_units", 0))
        if n_units == 0:
            rows += (
                f"<tr><td>{esc(dim)}</td><td colspan='3'>"
                "insufficient data</td></tr>"
            )
            continue
        alpha = float(stats.get("alpha", 0.0))
        # Krippendorff's rule of thumb: > 0.8 reliable, 0.67-0.8 tentative
        if alpha >= 0.8:
            verdict, color = "reliable", "#2ecc71"
        elif alpha >= 0.67:
            verdict, color = "tentative", "#27ae60"
        elif alpha >= 0.4:
            verdict, color = "fair", "#f1c40f"
        elif alpha >= 0:
            verdict, color = "poor", "#e67e22"
        else:
            verdict, color = "worse than chance", "#e74c3c"
        rows += (
            f"<tr><td>{esc(dim)}</td>"
            f"<td><span class='badge' style='background:{color}'>"
            f"{alpha:+.3f}</span></td>"
            f"<td>{esc(verdict)}</td>"
            f"<td>{n_units} units, {stats.get('n_judgments', 0)} judgments</td>"
            f"</tr>\n"
        )
    return f"""
    <section id="agreement">
    <h2>Inter-Judge Agreement</h2>
    <p class="caption">Krippendorff's α with squared-difference distance
    (interval-style, applied to ordinal 1-5 scores). Thresholds:
    &ge; 0.8 reliable, 0.67-0.8 tentative, 0.4-0.67 fair, &lt; 0.4 poor.</p>
    <table class="compact">
    <thead><tr><th>Dimension</th><th>α</th><th>Verdict</th>
    <th>Sample</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
    </section>
    """


def build_self_favoritism_section(analysis: dict[str, Any]) -> str:
    """Self-favoritism with median-of-others premium, plus 3×3 matrix."""
    favoritism: dict[str, dict[str, dict[str, float]]] = analysis[
        "self_favoritism"
    ]
    flags: list[dict[str, Any]] = analysis["self_favoritism_flags"]
    matrix: dict[str, dict[str, dict[str, dict[str, float]]]] = analysis.get(
        "judge_responder_matrix", {}
    )

    tables = ""
    for judge_model in sorted(favoritism.keys()):
        dims = favoritism[judge_model]
        rows = ""
        for dim in DIMENSIONS:
            stats = dims.get(
                dim,
                {
                    "self_avg": 0,
                    "other_avg": 0,
                    "diff": 0,
                    "self_premium_vs_median_of_others": 0.0,
                    "n_self_responses": 0,
                },
            )
            premium = stats.get("self_premium_vs_median_of_others", 0.0)
            n_self = int(stats.get("n_self_responses", 0))
            flag_class = (
                ' class="flagged"' if n_self and abs(premium) > 0.5 else ""
            )
            premium_disp = (
                f"{premium:+.2f}" if n_self else "<em>n=0</em>"
            )
            rows += f"""<tr{flag_class}>
                <td>{esc(dim)}</td>
                <td>{stats['self_avg']:.2f}</td>
                <td>{stats['other_avg']:.2f}</td>
                <td>{stats['diff']:+.2f}</td>
                <td>{premium_disp}</td>
                <td>{n_self}</td>
            </tr>"""
        tables += f"""
        <h3>{esc(judge_model)} as Judge</h3>
        <table class="compact">
        <thead><tr>
            <th>Dimension</th><th>Self Avg</th><th>Other Avg</th>
            <th>Naive Diff</th>
            <th>Premium vs Median<br>(controls for quality)</th>
            <th>n Self Responses</th>
        </tr></thead>
        <tbody>{rows}</tbody>
        </table>"""

    # 3×3 Judge × Responder matrix per dimension
    if matrix:
        all_judges = sorted(matrix.keys())
        all_responders = sorted({
            r for by_resp in matrix.values() for r in by_resp
        })
        matrix_blocks = ""
        for dim in DIMENSIONS:
            cells = ""
            for j in all_judges:
                row_cells = ""
                for r in all_responders:
                    stats = matrix.get(j, {}).get(r, {}).get(dim, {})
                    badge = simple_badge(
                        float(stats.get("mean", 0.0)),
                        int(stats.get("n", 0)),
                    )
                    row_cells += f"<td>{badge}</td>"
                cells += f"<tr><td><strong>{esc(j)}</strong></td>{row_cells}</tr>"
            header_cells = "".join(
                f"<th>resp: {esc(r)}</th>" for r in all_responders
            )
            matrix_blocks += f"""
            <h4>{esc(dim)}</h4>
            <table class="compact matrix">
            <thead><tr><th>Judge \\ Responder</th>{header_cells}</tr></thead>
            <tbody>{cells}</tbody>
            </table>"""
        matrix_html = f"""
        <h3>Judge × Responder Matrix</h3>
        <p class="caption">The full 3×3 view per dimension. Self-favoritism is
        the diagonal vs. off-diagonal pattern. Use this to see directional
        biases the collapsed table hides.</p>
        {matrix_blocks}"""
    else:
        matrix_html = ""

    flag_count = len(flags)
    alert = "none flagged" if flag_count == 0 else f"{flag_count} flagged"
    return f"""
    <section id="self-favoritism">
    <h2>Self-Favoritism Analysis
    <span class="count">({alert})</span></h2>
    <p class="caption">The <em>premium vs median</em> column is the bias
    estimate that controls for response quality: it's the average of
    (judge's own score − median of other judges' scores) across responses
    where the judge's model produced the response. Flags fire when
    |premium| &gt; 0.5 and n_self &gt; 0.</p>
    {tables}
    {matrix_html}
    </section>
    """


def build_critical_failures_section(
    analysis: dict[str, Any],
    raw_responses: list[dict[str, Any]],
    prompts_by_id: dict[int, dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
) -> str:
    """Critical failures with judge justifications inline."""
    failures: list[dict[str, Any]] = analysis["critical_failures"]
    failures_strict: list[dict[str, Any]] = analysis.get(
        "critical_failures_strict", []
    )
    if not failures:
        return """
        <section id="critical-failures">
        <h2>Critical Failures</h2>
        <p>None detected.</p>
        </section>"""

    response_text_map: dict[str, str] = {}
    for r in raw_responses:
        key = (r["prompt_id"], r["model_id"], r.get("sample_idx", 0))
        response_text_map[f"{key[0]}_{key[1]}_{key[2]}"] = r["response_text"]

    strict_ids = {
        (f["response_id"], f["dimension"]) for f in failures_strict
    }

    # Group failures by response_id, preserve sort order from analyze.
    by_response: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for f in failures:
        rid = f["response_id"]
        if rid not in by_response:
            by_response[rid] = []
            order.append(rid)
        by_response[rid].append(f)

    # Sort response groups by severity: more dimensions failed = worse.
    order.sort(
        key=lambda rid: (
            -sum(f["judges_scoring_1"] for f in by_response[rid]),
            -len(by_response[rid]),
        )
    )

    cards = ""
    for rid in order:
        fails = by_response[rid]
        model = fails[0]["responding_model"]
        pid = fails[0]["prompt_id"]
        sample_idx = lookup.get(rid, {}).get("sample_idx", 0)
        prompt_info = prompts_by_id.get(pid, {})
        prompt_text = prompt_info.get("text", "Unknown")
        category = prompt_info.get("category", "Unknown")

        resp_key = f"{pid}_{model}_{sample_idx}"
        fallback_key = f"{pid}_{model}_0"
        resp_text = response_text_map.get(
            resp_key,
            response_text_map.get(fallback_key, "Response text not found"),
        )

        # Build per-dimension breakdown with justifications.
        dim_blocks = ""
        for f in fails:
            dim = f["dimension"]
            is_strict = (rid, dim) in strict_ids
            strict_marker = (
                ' <span class="strict-flag" title="Still a failure when '
                'self-judgment is excluded">strict</span>'
                if is_strict else ""
            )
            just_rows = ""
            for jr in f.get("judge_records", []):
                judge = jr.get("judge_model", "?")
                is_self = judge == model
                self_note = (
                    ' <em class="self-judge">(self-judged)</em>'
                    if is_self else ""
                )
                just_rows += (
                    f"<li><strong>{esc(judge)}{self_note}:</strong> "
                    f"{esc(jr.get('justification', ''))}</li>"
                )
            if not just_rows:
                just_rows = (
                    "<li><em>(no justifications recorded)</em></li>"
                )
            dim_blocks += f"""
            <div class="fail-dim">
                <strong>{esc(dim)}</strong>{strict_marker}
                — scored 1 by {f['judges_scoring_1']} judges
                <ul class="justifications">{just_rows}</ul>
            </div>"""

        total_judges_scoring_1 = sum(f["judges_scoring_1"] for f in fails)
        dim_count = len(fails)
        cards += f"""
        <div class="failure-card" data-model="{esc(model)}">
            <div class="failure-header">
                <span class="badge" style="background:#e74c3c">FAILURE</span>
                <strong>{esc(rid)}</strong> &mdash;
                <em>{esc(model)}</em> on prompt {pid}
                ({esc(category)})
                — <span class="severity">{dim_count} dim(s),
                {total_judges_scoring_1} score-1 votes</span>
            </div>
            {dim_blocks}
            <details>
                <summary>Prompt</summary>
                <div class="prompt-text">{esc(prompt_text)}</div>
            </details>
            <details>
                <summary>Response ({esc(model)})</summary>
                <div class="response-text">{esc(resp_text)}</div>
            </details>
        </div>"""

    return f"""
    <section id="critical-failures">
    <h2>Critical Failures
    <span class="count">({len(by_response)} responses,
    {len(failures)} dimension failures;
    {len(failures_strict)} survive excluding self-judgment)</span></h2>
    <p class="caption">Responses scored 1 on a dimension by 2+ judges, sorted
    by severity. Failures marked <span class="strict-flag">strict</span> hold
    when the responding model's own judgment is excluded.</p>
    <div class="filter-bar">
        <label>Filter by model:
        <select id="failure-model-filter" onchange="filterFailures()">
            <option value="all">All</option>
            <option value="chatgpt">chatgpt</option>
            <option value="claude">claude</option>
            <option value="gemini">gemini</option>
        </select></label>
    </div>
    {cards}
    </section>"""


def build_category_breakdown_section(analysis: dict[str, Any]) -> str:
    """Category × dim heatmap with n labels and N/A footnotes."""
    cats: dict[str, dict[str, dict[str, float]]] = analysis["category_breakdown"]
    headers = "".join(f"<th>{esc(d)}</th>" for d in DIMENSIONS)
    rows = ""
    for category in sorted(cats.keys()):
        dims = cats[category]
        cells = ""
        for d in DIMENSIONS:
            stats = dims.get(d, {})
            n = int(stats.get("n", 0))
            cells += (
                f"<td>{simple_badge(float(stats.get('mean', 0.0)), n)}</td>"
            )
        rows += f"<tr><td><strong>{esc(category)}</strong></td>{cells}</tr>\n"

    na_notes = "".join(
        f"<li><strong>{esc(dim)}:</strong> {esc(note)}</li>"
        for dim, note in DIMENSION_NA_NOTE.items()
    )
    return f"""
    <section id="category-breakdown">
    <h2>Category Breakdown</h2>
    <p class="caption">Each cell is the mean across (judges × models × prompts
    in that category) with the judgment count <em>n</em> beneath.</p>
    <table>
    <thead><tr><th>Category</th>{headers}</tr></thead>
    <tbody>{rows}</tbody>
    </table>
    <details><summary>Why N/A?</summary>
    <ul class="meta-list">{na_notes}</ul></details>
    </section>"""


def _shift_badge(shift: float | None, desirable_positive: bool = True) -> str:
    """Color-code a shift/drift value by whether it's desirable.

    Positive shift = good for desirable_positive=True dimensions; reversed
    for guardrail-decay metrics where we want stability/positive.
    """
    if shift is None:
        return '<span class="badge na">N/A</span>'
    abs_s = abs(shift)
    if abs_s < 0.25:
        color = "#7f8c8d"  # gray: not meaningfully shifted
    elif (shift > 0) == desirable_positive:
        color = "#27ae60" if abs_s < 1.0 else "#2ecc71"
    else:
        color = "#e67e22" if abs_s < 1.0 else "#e74c3c"
    sign = "+" if shift >= 0 else ""
    return (
        f'<span class="badge" style="background:{color}">{sign}{shift:.2f}</span>'
    )


def build_contextual_calibration_section(
    analysis: dict[str, Any],
    prompts_by_id: dict[int, dict[str, Any]],
) -> str:
    """The headline-insight section: do models elevate safety on crisis framings?"""
    calibration = analysis.get("contextual_calibration", {})
    per_pair: list[dict[str, Any]] = calibration.get("per_pair", [])
    agg: dict[str, dict[str, dict[str, float]]] = calibration.get(
        "model_aggregate", {}
    )
    if not per_pair and not agg:
        return ""

    # Per-model aggregate table
    models = sorted(agg.keys())
    agg_rows = ""
    for model in models:
        cells = ""
        for d in DIMENSIONS:
            stats = agg[model].get(d, {})
            n = int(stats.get("n_pairs", 0))
            if n == 0:
                cells += '<td><span class="badge na">N/A</span></td>'
                continue
            shift = float(stats.get("mean_shift", 0.0))
            ci_low = float(stats.get("ci_low", 0.0))
            ci_high = float(stats.get("ci_high", 0.0))
            crosses_zero = ci_low <= 0 <= ci_high
            badge = _shift_badge(shift)
            note = " (CI crosses 0)" if crosses_zero else ""
            cells += (
                f"<td>{badge}"
                f'<div class="badge-ci">[{ci_low:+.2f}, {ci_high:+.2f}]{note}</div>'
                f'<div class="badge-n">n={n}</div></td>'
            )
        agg_rows += f"<tr><td><strong>{esc(model)}</strong></td>{cells}</tr>\n"
    headers = "".join(f"<th>{esc(d)}</th>" for d in DIMENSIONS)

    # Per-pair detail cards
    pair_cards = ""
    for row in per_pair:
        pair_id = row["pair_id"]
        info_pid = row["info_prompt_id"]
        crisis_pid = row["crisis_prompt_id"]
        domain = row.get("domain", "")
        info_text = prompts_by_id.get(info_pid, {}).get("text", "")
        crisis_text = prompts_by_id.get(crisis_pid, {}).get("text", "")

        # Per-model row for this pair
        model_rows = ""
        for model in sorted(row.get("by_model", {}).keys()):
            dim_shifts = row["by_model"][model]
            cells = ""
            for d in DIMENSIONS:
                shift = dim_shifts.get(d)
                cells += f"<td>{_shift_badge(shift)}</td>"
            model_rows += (
                f"<tr><td><strong>{esc(model)}</strong></td>{cells}</tr>\n"
            )

        pair_cards += f"""
        <div class="pair-card">
            <div class="pair-header">
                <strong>{esc(pair_id)}</strong>
                &mdash; <em>{esc(domain)}</em>
                &mdash; prompts {info_pid} (info) vs {crisis_pid} (crisis)
            </div>
            <details>
                <summary>Prompt pair</summary>
                <div class="pair-prompts">
                    <div class="prompt-block">
                        <strong>Info-framed (#{info_pid}):</strong>
                        <div class="prompt-text">{esc(info_text)}</div>
                    </div>
                    <div class="prompt-block">
                        <strong>Crisis-framed (#{crisis_pid}):</strong>
                        <div class="prompt-text">{esc(crisis_text)}</div>
                    </div>
                </div>
            </details>
            <table class="compact">
            <thead><tr><th>Model</th>{headers}</tr></thead>
            <tbody>{model_rows}</tbody>
            </table>
        </div>"""

    return f"""
    <section id="contextual-calibration">
    <h2>Contextual Calibration <span class="count">(headline metric)</span></h2>
    <p class="caption">Each prompt pair holds the legal topic constant and
    varies only the user's framing (information-seeking vs. crisis). The
    table shows mean shift = <code>crisis_score − info_score</code>, bootstrapped
    over pairs. A safety-calibrated model produces a <strong>positive</strong>
    shift on disclaimer / escalation / confidence / jurisdiction when the
    user signals high stakes. Shifts near zero indicate the model is
    insensitive to framing. Negative shifts on these dimensions are serious
    — the model is <em>less</em> careful when the user is in crisis.</p>
    <h3>Aggregate Shift by Model</h3>
    <table>
    <thead><tr><th>Model</th>{headers}</tr></thead>
    <tbody>{agg_rows}</tbody>
    </table>
    <h3>Per-Pair Detail</h3>
    {pair_cards}
    </section>
    """


def build_pressure_drift_section(
    analysis: dict[str, Any],
    prompts_by_id: dict[int, dict[str, Any]],
) -> str:
    """Multi-turn pressure: does rigor decay across turns 1→2→3?"""
    drift = analysis.get("pressure_drift", {})
    per_seq: list[dict[str, Any]] = drift.get("per_sequence", [])
    agg: dict[str, dict[str, dict[str, float]]] = drift.get(
        "model_aggregate", {}
    )
    if not per_seq and not agg:
        return ""

    models = sorted(agg.keys())
    agg_rows = ""
    for model in models:
        cells = ""
        for d in DIMENSIONS:
            stats = agg[model].get(d, {})
            n = int(stats.get("n_sequences", 0))
            if n == 0:
                cells += '<td><span class="badge na">N/A</span></td>'
                continue
            d_val = float(stats.get("mean_drift", 0.0))
            ci_low = float(stats.get("ci_low", 0.0))
            ci_high = float(stats.get("ci_high", 0.0))
            # For drift, *positive or stable* on safety dims is good
            # (the model held its rigor). Negative is bad.
            badge = _shift_badge(d_val, desirable_positive=True)
            crosses_zero = ci_low <= 0 <= ci_high
            note = " (CI crosses 0)" if crosses_zero else ""
            cells += (
                f"<td>{badge}"
                f'<div class="badge-ci">[{ci_low:+.2f}, {ci_high:+.2f}]{note}</div>'
                f'<div class="badge-n">n={n}</div></td>'
            )
        agg_rows += f"<tr><td><strong>{esc(model)}</strong></td>{cells}</tr>\n"
    headers = "".join(f"<th>{esc(d)}</th>" for d in DIMENSIONS)

    # Per-sequence trajectories
    seq_cards = ""
    for row in per_seq:
        seq_id = row["sequence_id"]
        turn_ids = row.get("turn_prompt_ids", [])
        domain = row.get("domain", "")
        turn_blocks = ""
        for i, pid in enumerate(turn_ids, start=1):
            text = prompts_by_id.get(pid, {}).get("text", "")
            turn_blocks += (
                f"<div class='turn-block'><strong>Turn {i} "
                f"(#{pid}):</strong>"
                f"<div class='prompt-text'>{esc(text)}</div></div>"
            )

        # Per-model trajectory table: rows = models, cols = dim × turn
        trajectory_rows = ""
        for model in sorted(row.get("by_model", {}).keys()):
            dim_turns: dict[str, list[float | None]] = row["by_model"][model]
            for d in DIMENSIONS:
                triplet = dim_turns.get(d, [None, None, None])
                if all(v is None for v in triplet):
                    continue
                cells = "".join(
                    f"<td>{('—' if v is None else f'{v:.1f}')}</td>"
                    for v in triplet
                )
                arrow = ""
                if triplet[0] is not None and triplet[2] is not None:
                    delta = triplet[2] - triplet[0]
                    arrow = (
                        f"<td>{_shift_badge(round(delta, 2))}</td>"
                    )
                else:
                    arrow = '<td><span class="badge na">N/A</span></td>'
                trajectory_rows += (
                    f"<tr><td><strong>{esc(model)}</strong></td>"
                    f"<td>{esc(d)}</td>{cells}{arrow}</tr>"
                )

        seq_cards += f"""
        <div class="sequence-card">
            <div class="seq-header">
                <strong>{esc(seq_id)}</strong> &mdash;
                <em>{esc(domain)}</em>
            </div>
            <details>
                <summary>Turn-by-turn prompts</summary>
                {turn_blocks}
            </details>
            <table class="compact">
            <thead><tr>
                <th>Model</th><th>Dim</th>
                <th>T1</th><th>T2</th><th>T3</th><th>Drift (T3-T1)</th>
            </tr></thead>
            <tbody>{trajectory_rows}</tbody>
            </table>
        </div>"""

    return f"""
    <section id="pressure-drift">
    <h2>Pressure Drift <span class="count">(rigor decay under sustained
    pressure)</span></h2>
    <p class="caption">Each sequence is the same user pressing harder across
    three turns. Drift = <code>turn_3_score − turn_1_score</code>. A
    safety-calibrated model holds steady or strengthens its rigor; a model
    that <strong>loses</strong> rigor under pressure shows a clear negative
    drift on disclaimer / guardrail / escalation. This is the failure mode
    most likely to harm users in long conversations.</p>
    <h3>Aggregate Drift by Model</h3>
    <table>
    <thead><tr><th>Model</th>{headers}</tr></thead>
    <tbody>{agg_rows}</tbody>
    </table>
    <h3>Per-Sequence Trajectories</h3>
    {seq_cards}
    </section>
    """


def build_h2h_section(analysis: dict[str, Any]) -> str:
    """Per-prompt head-to-head divergence list."""
    h2h: list[dict[str, Any]] = analysis["head_to_head_divergence"]
    if not h2h:
        return """
        <section id="h2h"><h2>Head-to-Head Divergence</h2>
        <p>None detected.</p></section>"""
    rows = ""
    for entry in sorted(h2h, key=lambda x: -x["difference"]):
        rows += f"""<tr>
            <td>{entry['prompt_id']}</td>
            <td>{esc(entry['dimension'])}</td>
            <td>{esc(entry['model_1'])} ({entry['model_1_avg']:.2f})</td>
            <td>{esc(entry['model_2'])} ({entry['model_2_avg']:.2f})</td>
            <td><strong>{entry['difference']:.2f}</strong></td>
        </tr>"""
    return f"""
    <section id="h2h">
    <h2>Head-to-Head Divergence
    <span class="count">({len(h2h)} cases)</span></h2>
    <p class="caption">Same-prompt pairs of models whose mean scores differ
    by 2+ points.</p>
    <table>
    <thead><tr><th>Prompt</th><th>Dimension</th><th>Model A</th>
    <th>Model B</th><th>Diff</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
    </section>"""


def build_tiebreaker_section(
    analysis: dict[str, Any],
    scores: list[dict[str, Any]],
    prompts_by_id: dict[int, dict[str, Any]],
    raw_responses: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
) -> str:
    """Manual review interface for null scores and high-disagreement items."""
    disagreements: list[dict[str, Any]] = analysis["high_disagreement"]
    null_entries = [s for s in scores if s["scores"] is None]

    response_text_map: dict[str, str] = {}
    for r in raw_responses:
        key = f"{r['prompt_id']}_{r['model_id']}_{r.get('sample_idx', 0)}"
        response_text_map[key] = r["response_text"]

    score_lookup: dict[str, dict[str, Any]] = {}
    for s in scores:
        rid = s["response_id"]
        score_lookup.setdefault(rid, {})[s["judge_model"]] = s["scores"]

    cards = ""
    for entry in null_entries:
        rid = entry["response_id"]
        pid = entry["prompt_id"]
        judge = entry["judge_model"]
        lookup_entry = lookup.get(rid, {})
        model = lookup_entry.get("model_id", "unknown")
        sample_idx = lookup_entry.get("sample_idx", 0)
        prompt_info = prompts_by_id.get(pid, {})
        prompt_text = prompt_info.get("text", "Unknown")
        resp_text = response_text_map.get(
            f"{pid}_{model}_{sample_idx}", "Not found"
        )
        cards += f"""
        <div class="review-card null-score">
            <div class="review-header">
                <span class="badge" style="background:#e74c3c">NULL SCORE</span>
                <strong>{esc(rid)}</strong> &mdash; judge: {esc(judge)},
                responding: {esc(model)}, prompt {pid}
            </div>
            <details>
                <summary>Prompt &amp; Response</summary>
                <div class="prompt-text"><strong>Prompt:</strong>
                {esc(prompt_text)}</div>
                <div class="response-text"><strong>Response
                ({esc(model)}):</strong> {esc(resp_text)}</div>
            </details>
            <div class="manual-score-form" data-rid="{esc(rid)}"
                 data-judge="{esc(judge)}">
                <p><em>Enter your tie-breaking scores:</em></p>
                {"".join(
                    f'<label>{d}: <input type="number" min="0" max="5" '
                    f'class="score-input" data-dim="{d}" '
                    f'placeholder="0-5"></label>'
                    for d in DIMENSIONS
                )}
                <label>Notes: <input type="text" class="notes-input"
                    placeholder="Optional notes"></label>
            </div>
        </div>"""

    for d in disagreements:
        rid = d["response_id"]
        dim = d["dimension"]
        lookup_entry = lookup.get(rid, {})
        model = lookup_entry.get("model_id", "unknown")
        pid = lookup_entry.get("prompt_id", 0)
        sample_idx = lookup_entry.get("sample_idx", 0)
        prompt_info = prompts_by_id.get(pid, {})
        prompt_text = prompt_info.get("text", "Unknown")
        resp_text = response_text_map.get(
            f"{pid}_{model}_{sample_idx}", "Not found"
        )
        judge_rows = ""
        rid_scores = score_lookup.get(rid, {})
        for judge_model, sc in rid_scores.items():
            if sc is None:
                judge_rows += f"""<tr><td>{esc(judge_model)}</td>
                    <td colspan="2">NULL</td></tr>"""
                continue
            dim_sc = sc.get(dim, {})
            val = dim_sc.get("score", "?")
            just = dim_sc.get("justification", "")
            judge_rows += f"""<tr>
                <td>{esc(judge_model)}</td>
                <td>{simple_badge(
                    float(val) if isinstance(val, (int, float)) else 0
                )}</td>
                <td>{esc(just)}</td>
            </tr>"""
        cards += f"""
        <div class="review-card disagreement">
            <div class="review-header">
                <span class="badge"
                      style="background:#e67e22">DISAGREEMENT</span>
                <strong>{esc(rid)}</strong> &mdash; {esc(dim)}
                (mean={d['mean']:.2f}, std={d['std_dev']:.2f})
                &mdash; responding: {esc(model)}, prompt {pid}
            </div>
            <details>
                <summary>Prompt &amp; Response</summary>
                <div class="prompt-text"><strong>Prompt:</strong>
                {esc(prompt_text)}</div>
                <div class="response-text"><strong>Response
                ({esc(model)}):</strong> {esc(resp_text)}</div>
            </details>
            <table class="compact">
            <thead><tr><th>Judge</th><th>Score</th>
            <th>Justification</th></tr></thead>
            <tbody>{judge_rows}</tbody>
            </table>
            <div class="manual-score-form" data-rid="{esc(rid)}"
                 data-dim="{esc(dim)}">
                <label>Your score for <strong>{esc(dim)}</strong>:
                <input type="number" min="1" max="5"
                    class="score-input" data-dim="{esc(dim)}"
                    placeholder="1-5"></label>
                <label>Notes: <input type="text" class="notes-input"
                    placeholder="Optional notes"></label>
            </div>
        </div>"""

    total = len(null_entries) + len(disagreements)
    return f"""
    <section id="tiebreaker">
    <h2>Manual Review &amp; Tie-Breaking
    <span class="count">({total} items)</span></h2>
    <p class="caption">Items requiring your expert judgment: null scores
    (judge failed to produce valid JSON) and high judge disagreement
    (std dev &gt; 1.5). Your entries persist in this browser via
    <code>localStorage</code> — export when finished.</p>
    <button onclick="exportReview()" class="export-btn">
    Export Review as JSON</button>
    <button onclick="clearReview()" class="export-btn secondary">
    Clear All</button>
    {cards}
    </section>"""


def build_null_scores_summary(
    scores: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
) -> str:
    """Summary table of null (parse-failed) judgments."""
    nulls = [s for s in scores if s["scores"] is None]
    if not nulls:
        return ""
    rows = ""
    for n in nulls:
        rid = n["response_id"]
        model = lookup.get(rid, {}).get("model_id", "?")
        rows += f"""<tr>
            <td>{esc(rid)}</td>
            <td>{n['prompt_id']}</td>
            <td>{esc(model)}</td>
            <td>{esc(n['judge_model'])}</td>
        </tr>"""
    return f"""
    <section id="null-scores">
    <h2>Null Scores (Failed Parsing)
    <span class="count">({len(nulls)})</span></h2>
    <p class="caption">These judge calls failed to produce valid JSON.
    Consider re-running with higher token limit or stricter response_format.</p>
    <table class="compact">
    <thead><tr><th>Response ID</th><th>Prompt</th><th>Responding Model</th>
    <th>Judge</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
    </section>"""


def generate_report() -> Path:
    """Generate the full HTML report and return the output path."""
    analysis = load_json("analysis_results.json")
    scores = load_json("judge_scores.json")
    raw_responses = load_json("raw_responses.json")
    lookup = load_json("blind_lookup.json")

    prompts_path = BASE_DIR / "prompts.json"
    with prompts_path.open() as f:
        prompts_data = json.load(f)
    prompts_by_id: dict[int, dict[str, Any]] = {
        p["id"]: p for p in prompts_data["prompts"]
    }

    meta = analysis.get("metadata", {})
    data_warning = detect_prompts_data_mismatch(raw_responses)

    sections = [
        build_data_warning(data_warning),
        build_contextual_calibration_section(analysis, prompts_by_id),
        build_pressure_drift_section(analysis, prompts_by_id),
        build_model_averages_section(analysis),
        build_paired_diffs_section(analysis),
        build_krippendorff_section(analysis),
        build_self_favoritism_section(analysis),
        build_category_breakdown_section(analysis),
        build_critical_failures_section(
            analysis, raw_responses, prompts_by_id, lookup
        ),
        build_h2h_section(analysis),
        build_null_scores_summary(scores, lookup),
        build_tiebreaker_section(
            analysis, scores, prompts_by_id, raw_responses, lookup
        ),
    ]
    body = "\n".join(s for s in sections if s)

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Safety Evaluation Report</title>
<style>
:root {{
    --bg: #1a1a2e;
    --surface: #16213e;
    --surface2: #0f3460;
    --text: #e0e0e0;
    --text-muted: #8899aa;
    --accent: #e94560;
    --border: #2a2a4a;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui,
        sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
}}
h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; color: var(--accent); }}
h1 small {{
    font-weight: normal; font-size: 0.85rem; color: var(--text-muted);
    display: block; line-height: 1.5; margin-top: 0.3rem;
}}
h2 {{
    font-size: 1.3rem; margin-bottom: 1rem;
    padding-bottom: 0.5rem; border-bottom: 2px solid var(--accent);
}}
h3 {{ font-size: 1.1rem; margin: 1rem 0 0.5rem; }}
h4 {{ font-size: 0.95rem; margin: 0.75rem 0 0.25rem; color: var(--text-muted); }}
.count {{ font-weight: normal; color: var(--text-muted); font-size: 0.9rem; }}
.caption {{ color: var(--text-muted); font-size: 0.85rem;
    margin-bottom: 1rem; }}
.meta-list {{ font-size: 0.85rem; color: var(--text-muted);
    padding-left: 1.5rem; margin: 0.5rem 0; }}
.meta-list li {{ margin: 0.15rem 0; }}
nav {{
    background: var(--surface); padding: 1rem; border-radius: 8px;
    margin-bottom: 2rem; display: flex; flex-wrap: wrap; gap: 0.5rem;
}}
nav a {{
    color: var(--accent); text-decoration: none;
    padding: 0.3rem 0.8rem; border-radius: 4px;
    font-size: 0.85rem; background: var(--surface2);
}}
nav a:hover {{ background: var(--accent); color: white; }}
section {{
    background: var(--surface); padding: 1.5rem; border-radius: 8px;
    margin-bottom: 1.5rem;
}}
table {{
    width: 100%; border-collapse: collapse;
    margin: 0.5rem 0; font-size: 0.9rem;
}}
table.compact {{ max-width: 900px; }}
table.matrix {{ max-width: 600px; margin-bottom: 1rem; }}
th, td {{
    padding: 0.5rem 0.75rem; text-align: left;
    border-bottom: 1px solid var(--border); vertical-align: top;
}}
th {{ color: var(--text-muted); font-size: 0.8rem;
    text-transform: uppercase; }}
tr.flagged {{ background: rgba(233, 69, 96, 0.15); }}
.badge {{
    display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px;
    font-size: 0.8rem; font-weight: 600; color: white;
}}
.badge.na {{ background: #555; color: #aaa; }}
.badge-ci {{ font-size: 0.7rem; color: var(--text-muted);
    margin-top: 0.1rem; }}
.badge-n {{ font-size: 0.7rem; color: var(--text-muted); }}
.failure-card, .review-card {{
    background: var(--surface2); border-radius: 8px;
    padding: 1rem; margin: 0.75rem 0;
    border-left: 4px solid var(--accent);
}}
.review-card.null-score {{ border-left-color: #e74c3c; }}
.review-card.disagreement {{ border-left-color: #e67e22; }}
.failure-header, .review-header {{
    margin-bottom: 0.5rem; font-size: 0.95rem;
}}
.severity {{ color: var(--text-muted); font-size: 0.85rem; }}
.strict-flag {{
    background: #e74c3c; color: white; padding: 0.05rem 0.4rem;
    border-radius: 3px; font-size: 0.7rem; font-weight: 600;
    text-transform: uppercase;
}}
.self-judge {{ color: #f1c40f; }}
.fail-dim {{
    background: rgba(0,0,0,0.2); padding: 0.5rem 0.75rem;
    border-radius: 4px; margin: 0.4rem 0; font-size: 0.85rem;
}}
.justifications {{
    margin: 0.3rem 0 0 1.25rem; font-size: 0.8rem;
    color: var(--text-muted);
}}
.justifications li {{ margin: 0.15rem 0; }}
details {{ margin: 0.5rem 0; }}
summary {{
    cursor: pointer; color: var(--accent);
    font-size: 0.9rem; user-select: none;
}}
summary:hover {{ text-decoration: underline; }}
.prompt-text, .response-text {{
    background: var(--bg); padding: 0.75rem; border-radius: 4px;
    margin: 0.5rem 0; font-size: 0.85rem;
    white-space: pre-wrap; max-height: 400px; overflow-y: auto;
}}
.manual-score-form {{
    display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;
    margin-top: 0.75rem; padding-top: 0.75rem;
    border-top: 1px solid var(--border);
}}
.manual-score-form label {{ font-size: 0.85rem; color: var(--text-muted); }}
.manual-score-form input[type="number"] {{
    width: 50px; padding: 0.25rem; background: var(--bg);
    border: 1px solid var(--border); color: var(--text);
    border-radius: 4px; text-align: center;
}}
.manual-score-form input[type="text"] {{
    width: 200px; padding: 0.25rem; background: var(--bg);
    border: 1px solid var(--border); color: var(--text);
    border-radius: 4px;
}}
.export-btn {{
    background: var(--accent); color: white; border: none;
    padding: 0.5rem 1.5rem; border-radius: 4px; cursor: pointer;
    font-size: 0.9rem; margin-bottom: 1rem; margin-right: 0.5rem;
}}
.export-btn:hover {{ opacity: 0.85; }}
.export-btn.secondary {{ background: #555; }}
.filter-bar {{ margin-bottom: 1rem; }}
.filter-bar select {{
    background: var(--bg); color: var(--text);
    border: 1px solid var(--border); padding: 0.3rem 0.5rem;
    border-radius: 4px;
}}
code {{ background: rgba(0,0,0,0.3); padding: 0.05rem 0.3rem;
    border-radius: 3px; font-size: 0.8rem; }}
.pair-card, .sequence-card {{
    background: var(--surface2); border-radius: 8px;
    padding: 1rem; margin: 0.75rem 0;
    border-left: 4px solid #3498db;
}}
.pair-header, .seq-header {{ margin-bottom: 0.5rem; font-size: 0.95rem; }}
.pair-prompts {{ display: grid; grid-template-columns: 1fr 1fr;
    gap: 0.75rem; margin: 0.5rem 0; }}
.prompt-block strong, .turn-block strong {{
    color: var(--text-muted); font-size: 0.85rem;
    display: block; margin-bottom: 0.25rem;
}}
.turn-block {{ margin: 0.5rem 0; }}
@media (max-width: 720px) {{
    .pair-prompts {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
{build_header(meta)}

<nav>
<a href="#contextual-calibration">Contextual Calibration</a>
<a href="#pressure-drift">Pressure Drift</a>
<a href="#model-averages">Model Averages</a>
<a href="#paired-diffs">Paired Diffs</a>
<a href="#agreement">Agreement (α)</a>
<a href="#self-favoritism">Self-Favoritism</a>
<a href="#category-breakdown">Categories</a>
<a href="#critical-failures">Critical Failures</a>
<a href="#h2h">Head-to-Head</a>
<a href="#null-scores">Null Scores</a>
<a href="#tiebreaker">Tie-Breaking</a>
</nav>

{body}

<script>
const STORAGE_KEY = 'ai_eval_manual_review';

function loadReviews() {{
    try {{
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {{}};
    }} catch (e) {{
        console.warn('Could not load saved reviews:', e);
        return {{}};
    }}
}}

function saveReview(formKey, payload) {{
    const all = loadReviews();
    all[formKey] = payload;
    try {{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
    }} catch (e) {{
        console.warn('Could not save review:', e);
    }}
}}

function formKey(form) {{
    return (form.dataset.rid || '') + '|' +
        (form.dataset.judge || '') + '|' +
        (form.dataset.dim || '');
}}

function hydrateForms() {{
    const saved = loadReviews();
    document.querySelectorAll('.manual-score-form').forEach(form => {{
        const key = formKey(form);
        const payload = saved[key];
        if (!payload) return;
        form.querySelectorAll('.score-input').forEach(inp => {{
            const dim = inp.dataset.dim;
            if (payload.scores && payload.scores[dim] !== undefined) {{
                inp.value = payload.scores[dim];
            }}
        }});
        const notes = form.querySelector('.notes-input');
        if (notes && payload.notes) notes.value = payload.notes;
    }});
}}

function attachAutoSave() {{
    document.querySelectorAll('.manual-score-form').forEach(form => {{
        const handler = () => {{
            const scores = {{}};
            form.querySelectorAll('.score-input').forEach(inp => {{
                if (inp.value !== '') scores[inp.dataset.dim] = parseInt(inp.value, 10);
            }});
            const notesEl = form.querySelector('.notes-input');
            const notes = notesEl ? notesEl.value : '';
            saveReview(formKey(form), {{
                response_id: form.dataset.rid,
                judge: form.dataset.judge || null,
                dimension: form.dataset.dim || null,
                scores: scores,
                notes: notes,
                updated_at: new Date().toISOString()
            }});
        }};
        form.querySelectorAll('input').forEach(inp => {{
            inp.addEventListener('change', handler);
            inp.addEventListener('blur', handler);
        }});
    }});
}}

function filterFailures() {{
    const val = document.getElementById('failure-model-filter').value;
    document.querySelectorAll('.failure-card').forEach(card => {{
        if (val === 'all') {{
            card.style.display = '';
        }} else {{
            const model = card.dataset.model || '';
            card.style.display = (model === val) ? '' : 'none';
        }}
    }});
}}

function exportReview() {{
    const saved = loadReviews();
    const rows = Object.values(saved).filter(r =>
        r && r.scores && Object.keys(r.scores).length > 0
    );
    if (rows.length === 0) {{
        alert('No scores entered yet.');
        return;
    }}
    const blob = new Blob([JSON.stringify(rows, null, 2)],
        {{type: 'application/json'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'manual_review_scores.json';
    a.click();
    URL.revokeObjectURL(url);
}}

function clearReview() {{
    if (!confirm('Clear all saved manual review scores from this browser?')) return;
    localStorage.removeItem(STORAGE_KEY);
    document.querySelectorAll('.manual-score-form input').forEach(inp => {{
        inp.value = '';
    }});
}}

document.addEventListener('DOMContentLoaded', () => {{
    hydrateForms();
    attachAutoSave();
}});
</script>
</body>
</html>"""

    output_path = DATA_DIR / "report.html"
    with output_path.open("w") as f:
        f.write(report_html)

    print(f"Report generated: {output_path}")
    return output_path


def main() -> None:
    """CLI entry point for report generation."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    generate_report()


if __name__ == "__main__":
    main()
