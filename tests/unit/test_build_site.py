"""Tests for report/build_site.py: the GitHub Pages build of the report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPORT_DIR = Path(__file__).resolve().parents[2] / "report"
sys.path.insert(0, str(REPORT_DIR))

import build_site  # noqa: E402
from render_print import TITLE  # noqa: E402

POST = "# [DRAFT v9]\n\n**Epistemic status:** short.\n\n## Finding\n\nBody text.\n"


@pytest.fixture()
def fake_root(tmp_path: Path) -> Path:
    """A repository layout holding every input the build reads."""
    root = tmp_path / "repo"
    (root / "report" / "site").mkdir(parents=True)
    (root / "figures").mkdir()
    (root / "report" / "post.md").write_text(POST)
    (root / "report" / build_site.PDF_NAME).write_bytes(b"%PDF-1.5")
    (root / "report" / "site" / "template.html").write_text("$body$")
    (root / "report" / "site" / "style.css").write_text("body {}")
    for name in build_site.FIGURES:
        (root / "figures" / name).write_text("<svg/>")
    return root


@pytest.fixture()
def fake_tools(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace git and pandoc; pandoc writes its stdin to the -o path."""
    calls: list[dict[str, Any]] = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, **kwargs})
        if command[0] == "git":
            return subprocess.CompletedProcess(command, 0, "abc1234 2026-10-11\n", "")
        output = Path(command[command.index("-o") + 1])
        output.write_bytes(kwargs["input"])
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    return calls


def test_pandoc_command_includes_template_toc_and_metadata() -> None:
    command = build_site.pandoc_command(
        Path("t.html"), Path("out/index.html"), "abc1234", "2026-10-11"
    )
    assert command[:5] == ["pandoc", "-f", "gfm", "-t", "html5"]
    assert command[command.index("--template") + 1] == "t.html"
    assert "--toc" in command
    assert f"title={TITLE}" in command
    assert "commit=abc1234" in command
    assert "built=2026-10-11" in command


def test_build_writes_page_and_assets_from_cleaned_post(
    fake_root: Path, fake_tools: list[dict[str, Any]], tmp_path: Path
) -> None:
    out = tmp_path / "site"
    page = build_site.build(out, root=fake_root)
    assert page == out / "index.html"
    rendered = page.read_text()
    assert rendered.startswith("**Epistemic status:**")
    assert "[DRAFT" not in rendered
    expected = {"index.html", "style.css", build_site.PDF_NAME, build_site.MARKER}
    expected |= set(build_site.FIGURES)
    assert {p.name for p in out.iterdir()} == expected
    assert [c["command"][0] for c in fake_tools] == ["git", "pandoc"]


def test_build_replaces_previous_build(
    fake_root: Path, fake_tools: list[dict[str, Any]], tmp_path: Path
) -> None:
    out = tmp_path / "site"
    build_site.build(out, root=fake_root)
    (out / "stale.html").write_text("old")
    build_site.build(out, root=fake_root)
    assert not (out / "stale.html").exists()


def test_build_refuses_foreign_nonempty_directory(
    fake_root: Path, fake_tools: list[dict[str, Any]], tmp_path: Path
) -> None:
    out = tmp_path / "precious"
    out.mkdir()
    (out / "notes.txt").write_text("keep me")
    with pytest.raises(build_site.SiteBuildError, match="refusing to delete"):
        build_site.build(out, root=fake_root)
    assert (out / "notes.txt").read_text() == "keep me"


def test_build_missing_input_raises_site_build_error(
    fake_root: Path, fake_tools: list[dict[str, Any]], tmp_path: Path
) -> None:
    (fake_root / "report" / build_site.PDF_NAME).unlink()
    with pytest.raises(build_site.SiteBuildError, match="missing inputs"):
        build_site.build(tmp_path / "site", root=fake_root)


def test_build_pandoc_failure_raises_site_build_error(
    fake_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[0] == "git":
            return subprocess.CompletedProcess(command, 0, "abc1234 2026-10-11\n", "")
        raise FileNotFoundError("pandoc")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(build_site.SiteBuildError, match="pandoc failed"):
        build_site.build(tmp_path / "site", root=fake_root)


@pytest.mark.parametrize("stdout", ["", "abc1234\n", "a b c\n"])
def test_commit_info_malformed_git_output_raises(
    monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(build_site.SiteBuildError, match="unexpected git output"):
        build_site.commit_info(Path("."))


def test_commit_info_git_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(128, command)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(build_site.SiteBuildError, match="cannot read"):
        build_site.commit_info(Path("."))


def test_main_returns_one_on_build_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(out: Path) -> Path:
        raise build_site.SiteBuildError("boom")

    monkeypatch.setattr(build_site, "build", fail)
    assert build_site.main(["--out", str(tmp_path / "site")]) == 1
