"""Produce a print copy of a draft: publication text only, no markers.

The filter removes everything that is not publication text:

- the ``# [DRAFT ...]`` heading, the draft-status blockquote, and the
  title-candidates section (everything before the first line starting
  with ``**Epistemic status:**``);
- the numbers-lock appendix (the trailing ``---`` plus everything from
  ``### Numbers-lock appendix`` to end of file);
- inline draft markers such as ``[YOU]``, ``[DRAFTED ...]``,
  ``[REPO LINK pending]``, with any surrounding backticks;
- draft-only note lines listed in ``NOTE_LINES``.

Statistical intervals like ``[−0.39, −0.24]`` are untouched: markers
are matched by keyword, never by bare brackets.

Usage:
    # cleaned markdown on stdout
    python3 drafts/render_print.py < drafts/substack_post.md

    # print-ready PDF (pandoc + xelatex); title is left as two ruled
    # lines to write on, since the title decision is open
    python3 drafts/render_print.py --pdf drafts/substack_post.print.pdf \
        < drafts/substack_post.md

Print copies are gitignored; the markdown stays the single source of
truth.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

BODY_START = re.compile(r"^\*\*Epistemic status:\*\*")
APPENDIX_HEADING = re.compile(r"^#+\s+Numbers-lock appendix")

MARKER = re.compile(
    r"\s*`?\["
    r"(?:YOU|LW-ONLY|CUT-OK|PENDING|DRAFTED|REPO LINK|DRAFT v?\d*"
    r"|not for publication)"
    r"[^\]]*\]`?"
)

# Draft-only sentences that carry no publication content.
NOTE_LINES = [
    re.compile(r"^Future work\. Nothing here blocks publication\.$"),
]

# Two ruled lines at the top of the PDF to hand-write the title on.
TITLE_SLOT_TEX = r"""
\vspace*{\baselineskip}
\noindent{\color{gray}\rule{\textwidth}{0.4pt}}\\[2.2\baselineskip]
\noindent{\color{gray}\rule{\textwidth}{0.4pt}}
\vspace{2\baselineskip}
"""

# Tables carry five columns of intervals; footnotesize plus tighter
# column padding keeps them inside the text block.
HEADER_TEX = r"""
\usepackage{etoolbox}
\usepackage{xcolor}
\setlength{\tabcolsep}{4pt}
\AtBeginEnvironment{longtable}{\footnotesize}
"""


def clean(markdown: str) -> str:
    """Return publication text only: body between front matter and appendix."""
    lines = markdown.splitlines()

    start = next(
        (i for i, line in enumerate(lines) if BODY_START.match(line)), None
    )
    if start is None:
        raise SystemExit("render_print: no '**Epistemic status:**' body start found")

    end = next(
        (i for i, line in enumerate(lines) if APPENDIX_HEADING.match(line)),
        len(lines),
    )
    # Walk back over the separator introducing the appendix.
    while end > start and lines[end - 1].strip() in ("", "---"):
        end -= 1

    kept = []
    for line in lines[start:end]:
        if any(note.match(line) for note in NOTE_LINES):
            continue
        kept.append(MARKER.sub("", line))

    return "\n".join(kept).strip() + "\n"


def to_pdf(markdown: str, output: Path) -> None:
    """Render cleaned markdown to a print PDF via pandoc and xelatex."""
    with tempfile.TemporaryDirectory() as tmp:
        header = Path(tmp) / "header.tex"
        title_slot = Path(tmp) / "title_slot.tex"
        header.write_text(HEADER_TEX)
        title_slot.write_text(TITLE_SLOT_TEX)
        subprocess.run(
            [
                "pandoc",
                "-f",
                "gfm",
                "-o",
                str(output),
                "--pdf-engine=xelatex",
                "-V",
                "mainfont=Charter",
                "-V",
                "fontsize=11pt",
                "-V",
                "geometry:margin=1in",
                "-V",
                "linestretch=1.35",
                "-H",
                str(header),
                "--include-before-body",
                str(title_slot),
            ],
            input=markdown.encode(),
            check=True,
        )


def main() -> None:
    cleaned = clean(sys.stdin.read())
    if len(sys.argv) == 3 and sys.argv[1] == "--pdf":
        to_pdf(cleaned, Path(sys.argv[2]))
    elif len(sys.argv) == 1:
        sys.stdout.write(cleaned)
    else:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} [--pdf OUTPUT.pdf] < draft.md")


if __name__ == "__main__":
    main()
