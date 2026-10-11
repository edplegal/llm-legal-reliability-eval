"""Build the report's web page into ``_site/`` for GitHub Pages.

The page carries the same publication text as the PDF: ``report/post.md``
passes through ``render_print.clean`` and then pandoc, with the template and
stylesheet in ``report/site/``. The committed PDF and the two figure
variants are copied beside the page. The footer names the commit and its
date, so a reader can tell which version of the repository the page shows.

Usage:
    python report/build_site.py            # writes _site/
    python report/build_site.py --out DIR

Needs pandoc on PATH. The GitHub Pages workflow runs ``python reproduce.py``
before this script, so a page is only published when every number checks.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
from pathlib import Path

from render_print import DATE, SUBTITLE, TITLE, clean

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
REPO_NAME = "edplegal/llm-legal-reliability-eval"
REPO_URL = f"https://github.com/{REPO_NAME}"
AUTHOR = "edplegal"
PDF_NAME = "judge-bias-blind-legal-advice-evaluation.pdf"
FIGURES = ("judge_bias_light.svg", "judge_bias_dark.svg")
# Written into every build so a rebuild only ever deletes its own output.
MARKER = ".built-by-build-site"


class SiteBuildError(RuntimeError):
    """The page could not be built from the repository."""


def commit_info(root: Path) -> tuple[str, str]:
    """Return the short hash and ISO date of the checked-out commit."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%h %cs"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SiteBuildError(f"cannot read the current commit: {exc}") from exc
    fields = result.stdout.split()
    if len(fields) != 2:
        raise SiteBuildError(f"unexpected git output: {result.stdout!r}")
    return fields[0], fields[1]


def pandoc_command(template: Path, output: Path, commit: str, built: str) -> list[str]:
    """Return the pandoc invocation that renders cleaned Markdown to the page."""
    metadata = {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "date": DATE,
        "author": AUTHOR,
        "commit": commit,
        "built": built,
        "repo": REPO_URL,
        "repo-name": REPO_NAME,
        "pdf": PDF_NAME,
    }
    command = [
        "pandoc",
        "-f",
        "gfm",
        "-t",
        "html5",
        "--standalone",
        "--template",
        str(template),
        "--toc",
        "--toc-depth=2",
        "-o",
        str(output),
    ]
    for key, value in metadata.items():
        command += ["--metadata", f"{key}={value}"]
    return command


def prepare_output(out: Path) -> None:
    """Create an empty output directory, replacing only a previous build."""
    if out.exists():
        if not out.is_dir():
            raise SiteBuildError(f"{out} exists and is not a directory")
        if any(out.iterdir()) and not (out / MARKER).exists():
            raise SiteBuildError(
                f"{out} is not empty and was not written by this script; "
                "refusing to delete it"
            )
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("")


def build(out: Path, root: Path = ROOT) -> Path:
    """Write the page and its assets into ``out``; return the page path."""
    report = root / "report"
    sources = [report / "post.md", report / PDF_NAME, report / "site" / "style.css"]
    sources += [root / "figures" / name for name in FIGURES]
    missing = [str(path) for path in sources if not path.exists()]
    if missing:
        raise SiteBuildError(f"missing inputs: {', '.join(missing)}")

    commit, built = commit_info(root)
    markdown = clean((report / "post.md").read_text())

    prepare_output(out)
    page = out / "index.html"
    try:
        subprocess.run(
            pandoc_command(report / "site" / "template.html", page, commit, built),
            input=markdown.encode(),
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SiteBuildError(f"pandoc failed: {exc}") from exc

    shutil.copy2(report / "site" / "style.css", out / "style.css")
    shutil.copy2(report / PDF_NAME, out / PDF_NAME)
    for name in FIGURES:
        shutil.copy2(root / "figures" / name, out / name)
    logger.info("Built %s from commit %s (%s)", page, commit, built)
    return page


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Build the report web page for GitHub Pages."
    )
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        build(args.out)
    except SiteBuildError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
