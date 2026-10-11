"""The report page builds from the real post with the real pandoc."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "report"))

import build_site  # noqa: E402
from render_print import TITLE  # noqa: E402


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_build_real_post_renders_title_tables_and_toc(tmp_path: Path) -> None:
    page = build_site.build(tmp_path / "site", root=ROOT).read_text()
    assert f"<title>{TITLE}</title>" in page
    assert page.count("<table") >= 4
    assert 'href="#finding-1-every-judge-has-a-fingerprint"' in page
    assert "$" + "body$" not in page
