"""Render the README figure: judge grading style and self-preference.

Reads ``data/analysis_results.json`` and writes two SVGs (light and dark)
with no dependency beyond the standard library. Each panel is one rubric
dimension; the top row is grading style (a judge's deviation from the other
judges' median on answers its own model did not write), the bottom row is
self-preference (the same deviation on its own answers, minus its style).
A filled dot marks an interval that excludes zero; a hollow dot marks one
that includes it.

Usage: python figures/make_figure.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
JUDGES: list[tuple[str, str]] = [
    ("chatgpt", "GPT-5.5"),
    ("chatgpt_mini", "GPT-5.4-mini"),
    ("claude", "Claude Sonnet 5"),
    ("claude_haiku", "Claude Haiku 4.5"),
    ("gemini", "Gemini 3.5 Flash"),
    ("gemini_lite", "Gemini 3.1 Lite"),
]
DIMS: list[tuple[str, str]] = [
    ("disclaimer", "Disclaimer"),
    ("escalation", "Escalation"),
    ("confidence", "Confidence"),
    ("jurisdiction", "Jurisdiction"),
]
ROWS: list[tuple[str, str, str, str, str]] = [
    (
        "Grading style",
        "style_deviation",
        "style_ci_low",
        "style_ci_high",
        "points above (+) or below (−) the other judges' median, "
        "on answers its own model did not write",
    ),
    (
        "Self-preference",
        "net_self_premium",
        "net_ci_low",
        "net_ci_high",
        "the same deviation on its own answers, minus its grading style",
    ),
]
THEMES: dict[str, dict[str, str]] = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "muted": "#898781",
        "grid": "#e4e3df",
        "mark": "#2a78d6",
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#ffffff",
        "ink2": "#c3c2b7",
        "muted": "#898781",
        "grid": "#33332f",
        "mark": "#3987e5",
    },
}
X_MIN, X_MAX = -1.0, 1.2
PANEL_W, PANEL_H = 215, 150
LEFT, TOP, GAP_X, GAP_Y = 130, 126, 26, 58
WIDTH = LEFT + 4 * PANEL_W + 3 * GAP_X + 20
HEIGHT = TOP + 2 * PANEL_H + GAP_Y + 70
FONT = (
    "font-family='-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, "
    "Arial, sans-serif'"
)
TITLE = "Every judge grades on a scale of its own, and most favor their own answers"
SUBTITLE_1 = (
    "Points on the 5-point rubric scale. Bars are 95% bootstrap intervals "
    "over the 60 questions."
)
SUBTITLE_2 = (
    "Filled dot: the interval excludes zero. Hollow dot: the interval includes zero."
)


def esc(text: str) -> str:
    """Escape text for SVG."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x: float, y: float, body: str, size: float, fill: str, **extra: str) -> str:
    """One SVG text element."""
    attrs = " ".join(f"{k.replace('_', '-')}='{v}'" for k, v in extra.items())
    return (
        f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{fill}' {attrs}>"
        f"{esc(body)}</text>"
    )


def x_of(value: float) -> float:
    """Horizontal panel position of a value on the shared axis."""
    return (value - X_MIN) / (X_MAX - X_MIN) * PANEL_W


def panel(fav: dict[str, Any], row: int, col: int, theme: dict[str, str]) -> list[str]:
    """One dimension's panel for one row (style or self-preference)."""
    row_label, key, lo_key, hi_key, _ = ROWS[row]
    dim, dim_label = DIMS[col]
    x0 = LEFT + col * (PANEL_W + GAP_X)
    y0 = TOP + row * (PANEL_H + GAP_Y)
    out = [f"<g transform='translate({x0},{y0})'>"]
    if row == 0:
        out.append(
            text(
                PANEL_W / 2,
                -30,
                dim_label,
                12.5,
                theme["ink"],
                font_weight="600",
                text_anchor="middle",
            )
        )
    for tick in (-1.0, -0.5, 0.0, 0.5, 1.0):
        tx = x_of(tick)
        stroke = theme["muted"] if tick == 0 else theme["grid"]
        out.append(
            f"<line x1='{tx:.1f}' y1='0' x2='{tx:.1f}' y2='{PANEL_H}' "
            f"stroke='{stroke}' stroke-width='1'/>"
        )
        label = f"{tick:+.1f}" if tick else "0"
        out.append(
            text(tx, PANEL_H + 16, label, 10.5, theme["muted"], text_anchor="middle")
        )
    for j, (judge, judge_label) in enumerate(JUDGES):
        cy = (j + 0.5) * PANEL_H / len(JUDGES)
        if col == 0:
            out.append(
                text(-10, cy + 4, judge_label, 11.5, theme["ink2"], text_anchor="end")
            )
        cell = fav[judge][dim]
        v, lo, hi = cell[key], cell[lo_key], cell[hi_key]
        significant = lo > 0 or hi < 0
        out.append(
            f"<line x1='{x_of(lo):.1f}' y1='{cy:.1f}' x2='{x_of(hi):.1f}' "
            f"y2='{cy:.1f}' stroke='{theme['mark']}' stroke-width='2' "
            "stroke-linecap='round'/>"
        )
        fill = theme["mark"] if significant else theme["surface"]
        tip = (
            f"{judge_label}, {dim_label}, {row_label.lower()}: "
            f"{v:+.2f} [{lo:+.2f}, {hi:+.2f}]"
        )
        out.append(
            f"<circle cx='{x_of(v):.1f}' cy='{cy:.1f}' r='4.5' fill='{fill}' "
            f"stroke='{theme['mark']}' stroke-width='2'><title>{esc(tip)}</title>"
            "</circle>"
        )
    out.append("</g>")
    return out


def render(results: dict[str, Any], theme: dict[str, str]) -> str:
    """Return the SVG document for one theme."""
    fav = results["self_favoritism"]
    meta = results["metadata"]
    out: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{WIDTH}' height='{HEIGHT}' "
        f"viewBox='0 0 {WIDTH} {HEIGHT}' role='img' aria-labelledby='t d' {FONT}>",
        "<title id='t'>Judge grading style and self-preference, by judge and "
        "dimension</title>",
        "<desc id='d'>Dot and interval plot. Six judges on the vertical axis, four "
        "rubric dimensions as columns, grading style on the top row and "
        "self-preference on the bottom row. Filled dots mark 95 percent intervals "
        "that exclude zero.</desc>",
        f"<rect width='{WIDTH}' height='{HEIGHT}' fill='{theme['surface']}'/>",
        text(LEFT, 30, TITLE, 17, theme["ink"], font_weight="600"),
        text(LEFT, 52, SUBTITLE_1, 12.5, theme["ink2"]),
        text(LEFT, 70, SUBTITLE_2, 12.5, theme["ink2"]),
    ]
    for row, (row_label, _, _, _, row_desc) in enumerate(ROWS):
        y0 = TOP + row * (PANEL_H + GAP_Y)
        out.append(
            text(LEFT - 118, y0 - 10, row_label, 13, theme["ink"], font_weight="600")
        )
        out.append(text(LEFT + 112, y0 - 10, row_desc, 11, theme["ink2"]))
        for col in range(len(DIMS)):
            out.extend(panel(fav, row, col, theme))
    source = (
        f"Source: data/analysis_results.json (analyze v{meta['analyze_version']}, "
        f"seed {meta['bootstrap_seed']}, {meta['bootstrap_iterations']} bootstrap "
        f"draws); {meta['n_judgments_valid']} valid grades of "
        f"{meta['n_judgments_total']}."
    )
    out.append(text(LEFT, HEIGHT - 22, source, 10.5, theme["muted"]))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    """Write figures/judge_bias_light.svg and figures/judge_bias_dark.svg."""
    results = json.loads((ROOT / "data" / "analysis_results.json").read_text())
    for name, theme in THEMES.items():
        path = ROOT / "figures" / f"judge_bias_{name}.svg"
        path.write_text(render(results, theme))
        sys.stdout.write(f"wrote {path.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
