"""Numbers lock: every number in the README and the report must match the data.

The report (``report/post.md``) and the README state statistics in prose and
in tables. This module regenerates each of those statements from the released
analysis files, in the exact wording the documents use, and reports every
statement that no longer appears. It also checks the reverse direction for
tables: every table row in the report whose first cell names a judge, an arm,
or a vendor line must be one of the regenerated rows. A number edited by hand
in either document, or a change in the data that moves a reported number,
makes ``reproduce.py`` and the integration test fail.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ai_eval.analyze import get_score_value, mean
from ai_eval.schema import APPLICABLE_DIMENSIONS

if TYPE_CHECKING:
    from pathlib import Path

README = "README.md"
POST = "report/post.md"

JUDGE_NAMES: dict[str, str] = {
    "chatgpt": "GPT-5.5",
    "chatgpt_mini": "GPT-5.4-mini",
    "claude": "Claude Sonnet 5",
    "claude_haiku": "Claude Haiku 4.5",
    "gemini": "Gemini 3.5 Flash",
    "gemini_lite": "Gemini 3.1 Lite",
}
JUDGE_ORDER: tuple[str, ...] = tuple(JUDGE_NAMES)
VENDOR_NAMES: dict[str, str] = {
    "claude": "Claude",
    "chatgpt": "OpenAI",
    "gemini": "Gemini",
}
ERA_ORDER: tuple[str, ...] = ("gen4", "gen46", "gen5")
WORKED_PAIR = "P04"
WORKED_MODEL = "claude"
NUMBER_WORDS: dict[int, str] = {
    5: "five",
    9: "nine",
    11: "eleven",
    14: "fourteen",
    15: "fifteen",
    24: "twenty-four",
    25: "twenty-five",
}


@dataclass(frozen=True)
class Claim:
    """One statement a document must contain, in the document's own wording."""

    name: str
    text: str
    docs: tuple[str, ...]


@dataclass(frozen=True)
class Inputs:
    """The released artifacts the claims are regenerated from."""

    results: dict[str, Any]
    bridge: dict[str, Any]
    refill: dict[str, Any]
    gen46: dict[str, Any]
    judge_scores: list[dict[str, Any]]
    lookup: dict[str, dict[str, Any]]
    prompts: dict[int, dict[str, Any]]


def fmt(value: float) -> str:
    """Signed two-decimal number with an ASCII minus (documents are normalized)."""
    return f"{value:+.2f}"


def normalize(text: str) -> str:
    """Collapse whitespace and map the typographic minus to ASCII."""
    return re.sub(r"\s+", " ", text.replace("−", "-"))


def ceil_hundredth(value: float) -> float:
    """Smallest multiple of 0.01 strictly greater than ``value``."""
    return math.floor(value * 100 + 1) / 100


def word(n: int, capital: bool = False) -> str:
    """Number word used by the report, falling back to digits."""
    w = NUMBER_WORDS.get(n, str(n))
    return w[0].upper() + w[1:] if capital else w


def load_inputs(root: Path) -> Inputs:
    """Read every artifact the claims depend on."""
    data = root / "data"
    prompts_raw = json.loads((root / "prompts.json").read_text())["prompts"]
    return Inputs(
        results=json.loads((data / "analysis_results.json").read_text()),
        bridge=json.loads((data / "bridge_results.json").read_text()),
        refill=json.loads((data / "null_refill_results.json").read_text()),
        gen46=json.loads(
            (data / "archive" / "gen46" / "gen46_analysis_results.json").read_text()
        ),
        judge_scores=json.loads((data / "judge_scores.json").read_text()),
        lookup=json.loads((data / "blind_lookup.json").read_text()),
        prompts={p["id"]: p for p in prompts_raw},
    )


def _cell(value: float, lo: float, hi: float) -> str:
    bold = lo > 0 or hi < 0
    head = f"**{fmt(value)}**" if bold else fmt(value)
    return f"{head} [{fmt(lo)}, {fmt(hi)}]"


def _iv(rec: dict[str, Any], value: str, lo: str, hi: str) -> str:
    """Cell text from a record's value and interval keys."""
    return _cell(rec[value], rec[lo], rec[hi])


def _row(label: str, cells: list[str]) -> str:
    return f"| {label} | " + " | ".join(cells) + " |"


def table_rows(inputs: Inputs) -> dict[str, list[str]]:
    """The four tables in the report, regenerated row by row."""
    fav = inputs.results["self_favoritism"]
    crisis = inputs.results["contextual_calibration"]["model_aggregate"]
    by_era = inputs.bridge["crisis_by_era"]
    rows: dict[str, list[str]] = {
        "style": [],
        "net": [],
        "crisis": [],
        "crisis_by_era": [],
    }
    for judge, name in JUDGE_NAMES.items():
        cells = fav[judge]
        rows["style"].append(
            _row(
                name,
                [
                    _iv(cells[d], "style_deviation", "style_ci_low", "style_ci_high")
                    for d in APPLICABLE_DIMENSIONS
                ],
            )
        )
        rows["net"].append(
            _row(
                name,
                [
                    _iv(cells[d], "net_self_premium", "net_ci_low", "net_ci_high")
                    for d in APPLICABLE_DIMENSIONS
                ],
            )
        )
        rows["crisis"].append(
            _row(
                name,
                [
                    _iv(crisis[judge][d], "mean_shift", "ci_low", "ci_high")
                    for d in ("disclaimer", "escalation")
                ],
            )
        )
    for model, label in VENDOR_NAMES.items():
        rows["crisis_by_era"].append(
            _row(
                label,
                [
                    _iv(by_era[e][model]["disclaimer"], "mean", "ci_low", "ci_high")
                    for e in ERA_ORDER
                ],
            )
        )
    return rows


def worked_pair_means(inputs: Inputs) -> tuple[float, float]:
    """Panel disclaimer means for the worked pair's calm and crisis answers."""
    roles = {
        p["pair_role"]: pid
        for pid, p in inputs.prompts.items()
        if p.get("pair_id") == WORKED_PAIR
    }
    sums: dict[int, list[float]] = {roles["info"]: [], roles["crisis"]: []}
    for record in inputs.judge_scores:
        if record["scores"] is None:
            continue
        entry = inputs.lookup[record["response_id"]]
        if entry["model_id"] != WORKED_MODEL or entry["prompt_id"] not in sums:
            continue
        val = get_score_value(record["scores"], "disclaimer")
        if val is not None:
            sums[entry["prompt_id"]].append(val)
    return mean(sums[roles["info"]]), mean(sums[roles["crisis"]])


def _significant_nets(fav: dict[str, Any]) -> tuple[int, int]:
    sig = pos = 0
    for judge in JUDGE_ORDER:
        for dim in APPLICABLE_DIMENSIONS:
            c = fav[judge][dim]
            if c["net_ci_low"] > 0 or c["net_ci_high"] < 0:
                sig += 1
                pos += c["net_self_premium"] > 0
    return sig, pos


def _interval_phrase(rec: dict[str, Any], value: str, lo: str, hi: str) -> str:
    """'+0.21 with an interval from -0.40 to +0.85', as the report phrases it."""
    return f"{fmt(rec[value])} with an interval from {fmt(rec[lo])} to {fmt(rec[hi])}"


def _bracket(rec: dict[str, Any], value: str, lo: str, hi: str) -> str:
    """'-0.66 [-1.09, -0.25]', as the README phrases it."""
    return f"{fmt(rec[value])} [{fmt(rec[lo])}, {fmt(rec[hi])}]"


def _panel_claims(inputs: Inputs) -> list[Claim]:
    r = inputs.results
    meta = r["metadata"]
    fav = r["self_favoritism"]
    crisis = r["contextual_calibration"]["model_aggregate"]
    drift = r["pressure_drift"]["model_aggregate"]
    avgs = r["model_averages"]
    alphas = [a["alpha"] for a in r["krippendorff_alpha"].values()]
    var = r["variance_components"]["pooled"]
    bridge_meta = inputs.bridge["metadata"]["eras"]["gen5"]
    n_bridge = bridge_meta["n_judgments_frozen"]
    n_total = meta["n_judgments_total"]
    n_null = meta["n_judgments_null"]
    n_sig, n_pos = _significant_nets(fav)
    both = (README, POST)
    post = (POST,)
    readme = (README,)
    non_gemini = ("chatgpt", "chatgpt_mini", "claude", "claude_haiku")
    outside = [avgs[m]["disclaimer"]["mean"] for m in non_gemini]
    claude_style = [fav["claude"][d]["style_deviation"] for d in APPLICABLE_DIMENSIONS]
    turns = drift["gemini"]["disclaimer"]["turn_means"]
    pct = {k: round(var[k]) for k in ("pct_prompt", "pct_judge", "pct_response")}
    prev = round(inputs.gen46["variance_components"]["pooled"]["pct_response"])
    haiku = crisis["claude_haiku"]["disclaimer"]
    top_prompt = Counter(
        inputs.lookup[h["response_id"]]["prompt_id"] for h in r["high_disagreement"]
    ).most_common(1)[0][1]
    n_hd = len(r["high_disagreement"])
    calm, crisis_mean = worked_pair_means(inputs)
    return [
        Claim("grade total", f"{n_total + n_bridge:,} grades", both),
        Claim("panel grades", f"{n_total:,} grades", post),
        Claim("bridge grades", f"{n_bridge:,} additional grades", post),
        Claim("answers", f"{len(inputs.lookup):,} answers", both),
        Claim("questions", f"{meta['n_prompts']} legal questions", post),
        Claim("nulls", f"{word(n_null, True)} came back unparseable", post),
        Claim(
            "nulls, limitation",
            f"{word(n_null, True)} of {n_total:,} panel grades and "
            f"{word(bridge_meta['n_judgments_null'])} of {n_bridge:,} bridge grades",
            post,
        ),
        Claim("significant nets", f"{n_sig} of 24 measurements exclude zero", post),
        Claim(
            "significant nets, prose",
            f"{word(n_sig, True)} of these {word(24)} measurements exclude zero. "
            f"All {word(n_pos)} are positive",
            post,
        ),
        Claim("significant nets, readme", f"{n_sig} of 24", readme),
        Claim(
            "mini disclaimer style",
            "disclaimer style is "
            + fmt(fav["chatgpt_mini"]["disclaimer"]["style_deviation"]),
            post,
        ),
        Claim(
            "mini disclaimer style, readme",
            fmt(fav["chatgpt_mini"]["disclaimer"]["style_deviation"]),
            readme,
        ),
        Claim(
            "claude style range, readme",
            f"{abs(max(claude_style)):.2f} to {abs(min(claude_style)):.2f}",
            readme,
        ),
        Claim(
            "haiku crisis",
            f"{fmt(haiku['mean_shift'])}, with an interval from "
            f"{fmt(haiku['ci_low'])} to {fmt(haiku['ci_high'])}",
            post,
        ),
        Claim(
            "gpt-5.5 crisis",
            "disclaimer shift is "
            + _interval_phrase(
                crisis["chatgpt"]["disclaimer"], "mean_shift", "ci_low", "ci_high"
            ),
            post,
        ),
        Claim(
            "sonnet crisis, readme",
            _bracket(crisis["claude"]["disclaimer"], "mean_shift", "ci_low", "ci_high"),
            readme,
        ),
        Claim(
            "gemini flash turns",
            f"starts near {turns[0]:.1f} in the first turn and falls to "
            f"{turns[2]:.1f} by the third",
            post,
        ),
        Claim(
            "variance, finding 4",
            f"the question accounts for {pct['pct_prompt']} percent of grading "
            "variance, "
            f"the judge for {pct['pct_judge']} percent, and the re-asked answer for "
            f"{pct['pct_response']} percent",
            post,
        ),
        Claim(
            "variance, tldr",
            f"the question accounts for {pct['pct_prompt']} percent, the judge for "
            f"{pct['pct_judge']} percent, and the model's re-rolled answer for "
            f"{pct['pct_response']} percent",
            post,
        ),
        Claim(
            "variance, previous run",
            f"rose from {prev} percent in the previous run to "
            f"{pct['pct_response']} percent here",
            post,
        ),
        Claim(
            "alpha range", f"it runs {min(alphas):.2f} to {max(alphas):.2f} here", post
        ),
        Claim(
            "alpha range, limitation",
            f"Alpha runs {min(alphas):.2f} to {max(alphas):.2f} by dimension",
            post,
        ),
        Claim(
            "disclaimer means outside gemini",
            f"run {min(outside):.1f} to {max(outside):.1f} out of 5",
            post,
        ),
        Claim(
            "gemini disclaimer means",
            f"outlier at {avgs['gemini']['disclaimer']['mean']:.1f} and "
            f"{avgs['gemini_lite']['disclaimer']['mean']:.1f}",
            post,
        ),
        Claim(
            "mini disclaimer mean",
            f"still {avgs['chatgpt_mini']['disclaimer']['mean']:.1f} out of 5",
            post,
        ),
        Claim(
            "critical failures",
            f"{len(r['critical_failures'])} answer-dimension pairs were scored "
            "1 out of 5 "
            "by at least two of six",
            post,
        ),
        Claim(
            "high disagreement count",
            f"{word(n_hd, True)} answers produced guardrail grades",
            post,
        ),
        Claim(
            "flags from one question",
            f"{word(top_prompt, True)} of the {word(n_hd)} flags come from "
            "one question",
            post,
        ),
        Claim(
            "limitation 8, sonnet",
            "escalation style deviation is "
            + _interval_phrase(
                fav["claude"]["escalation"],
                "style_deviation",
                "style_ci_low",
                "style_ci_high",
            ),
            post,
        ),
        Claim(
            "limitation 8, lite",
            "escalation self-preference is "
            + _interval_phrase(
                fav["gemini_lite"]["escalation"],
                "net_self_premium",
                "net_ci_low",
                "net_ci_high",
            ),
            post,
        ),
        Claim(
            "worked pair, calm",
            f"grades its disclaimer behavior {calm:.1f} out of 5",
            post,
        ),
        Claim("worked pair, crisis", f"The panel grades it {crisis_mean:.1f}", post),
    ]


def _bridge_claims(inputs: Inputs) -> list[Claim]:
    levels = inputs.bridge["levels"]
    steps = inputs.bridge["steps"]
    by_era = inputs.bridge["crisis_by_era"]
    s4_46 = steps["gen4->gen46"]["claude"]["disclaimer"]
    s4_5 = steps["gen4->gen5"]["claude"]["disclaimer"]
    max_control = max(
        abs(steps["gen4->gen46"][m][d]["mean"])
        for m in ("chatgpt", "gemini")
        for d in APPLICABLE_DIMENSIONS
    )
    chain = [levels[e]["claude"]["disclaimer"]["mean"] for e in ERA_ORDER]
    return [
        Claim(
            "claude level chain",
            f"{chain[0]:.2f} at Sonnet 4, down to {chain[1]:.2f} at Sonnet 4.6, "
            f"back up to {chain[2]:.2f} at Sonnet 5",
            (POST,),
        ),
        Claim(
            "sonnet 4 to 4.6",
            f"disclaimer level fell {abs(s4_46['mean']):.2f} points from Sonnet 4, "
            f"with an interval from {fmt(s4_46['ci_low'])} to {fmt(s4_46['ci_high'])}",
            (POST,),
        ),
        Claim(
            "sonnet 4 to 5",
            "The full Sonnet 4 to Sonnet 5 change is "
            + _interval_phrase(s4_5, "mean", "ci_low", "ci_high"),
            (POST,),
        ),
        Claim(
            "controls",
            f"The controls moved at most {max_control:.2f} points on any dimension",
            (POST,),
        ),
        Claim(
            "sonnet crisis under frozen judges, readme",
            _bracket(
                by_era["gen5"]["claude"]["disclaimer"], "mean", "ci_low", "ci_high"
            ),
            (README,),
        ),
    ]


def _refill_claims(inputs: Inputs) -> list[Claim]:
    fills = inputs.refill["refills"]

    def fam(fill: str, name: str) -> float:
        return float(fills[fill]["families"][name]["max_abs_change"])

    tight = max(fam(f, n) for f in fills for n in ("crisis", "disclaimer_means"))
    loose = max(
        [
            fam(f, n)
            for f in fills
            for n in ("confidence_drift", "disclaimer_turn_means")
        ]
        + [float(fills[f]["bridge"]["max_abs_change"]) for f in fills]
    )
    style_max = max(fam(f, "style") for f in fills)
    flip = next(
        x
        for x in fills["fill_5"]["significance_flips"]
        if x["cell"] == "style/gemini/disclaimer"
    )
    post = (POST,)
    return [
        Claim(
            "refill, tight bound",
            "moves every crisis shift and every model average in this post by "
            "less than "
            f"{ceil_hundredth(tight):.2f}",
            post,
        ),
        Claim(
            "refill, loose bound",
            "every drift, turn mean, and frozen-judge number by less than "
            f"{ceil_hundredth(loose):.2f}",
            post,
        ),
        Claim("refill, style bound", f"cells move up to {style_max:.2f}", post),
        Claim(
            "refill, gemini cell",
            f"disclaimer style, {fmt(flip['before_value'])}, would read "
            f"{fmt(flip['after_value'])}",
            post,
        ),
        Claim(
            "refill, limitation tight",
            f"model average moved by less than {ceil_hundredth(tight):.2f}",
            post,
        ),
        Claim(
            "refill, limitation loose",
            f"frozen-judge number by less than {ceil_hundredth(loose):.2f}",
            post,
        ),
        Claim("refill, limitation style", f"cells moved up to {style_max:.2f}", post),
    ]


def expected_claims(inputs: Inputs) -> list[Claim]:
    """Every numeric statement the documents make, regenerated from the data."""
    claims = _panel_claims(inputs) + _bridge_claims(inputs) + _refill_claims(inputs)
    for table, rows in table_rows(inputs).items():
        for i, row in enumerate(rows):
            claims.append(Claim(f"table {table} row {i + 1}", row, (POST,)))
    return claims


def _row_labels() -> set[str]:
    return set(JUDGE_NAMES.values()) | set(VENDOR_NAMES.values())


def check_documents(root: Path) -> list[str]:
    """Return one message per claim that a document fails to contain."""
    inputs = load_inputs(root)
    docs = {name: normalize((root / name).read_text()) for name in (README, POST)}
    failures: list[str] = []
    for claim in expected_claims(inputs):
        for doc in claim.docs:
            if normalize(claim.text) not in docs[doc]:
                failures.append(f"{doc}: missing [{claim.name}] {claim.text}")
    generated = {normalize(row) for rows in table_rows(inputs).values() for row in rows}
    labels = _row_labels()
    for line in (root / POST).read_text().splitlines():
        if not line.startswith("| "):
            continue
        first = line.split("|")[1].strip()
        if first in labels and normalize(line.strip()) not in generated:
            failures.append(
                f"{POST}: table row not regenerated from data: {line.strip()}"
            )
    return failures


def claim_count(root: Path) -> int:
    """Number of claims checked, for reporting."""
    return len(expected_claims(load_inputs(root)))
