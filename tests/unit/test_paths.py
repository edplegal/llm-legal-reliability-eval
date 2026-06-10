"""Tests for shared path resolution and provenance-safe IO."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ai_eval.paths import (
    base_dir,
    data_dir,
    read_json,
    rotate_to_legacy,
    write_json_atomic,
    write_json_with_rotation,
    write_text_with_rotation,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestBaseDir:
    """Tests for project-root resolution."""

    def test_env_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AI_EVAL_BASE_DIR relocates the project root."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        assert base_dir() == tmp_path
        assert data_dir() == tmp_path / "data"

    def test_default_is_repo_checkout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without the env var, the root is the repo containing the package."""
        monkeypatch.delenv("AI_EVAL_BASE_DIR", raising=False)
        root = base_dir()
        assert (root / "src" / "ai_eval").is_dir()


class TestAtomicWrite:
    """Tests for write_json_atomic."""

    def test_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        write_json_atomic(path, {"a": 1})
        assert read_json(path) == {"a": 1}

    def test_no_tmp_file_left_behind(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        write_json_atomic(path, [1, 2, 3])
        assert list(tmp_path.iterdir()) == [path]

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "deeper" / "out.json"
        write_json_atomic(path, {})
        assert path.exists()


class TestRotateToLegacy:
    """Tests for the never-silently-overwrite rotation helper."""

    def test_missing_file_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        assert rotate_to_legacy(tmp_path / "data" / "nope.json") is None

    def test_existing_file_moves_with_date_suffix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        data = tmp_path / "data"
        data.mkdir()
        artifact = data / "scores.json"
        artifact.write_text("[]")

        dest = rotate_to_legacy(artifact)

        assert dest is not None
        assert not artifact.exists()
        assert dest.parent == data / "legacy"
        assert dest.name.startswith("scores_")
        assert dest.read_text() == "[]"

    def test_same_day_rotation_does_not_collide(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A second rotation on the same day gets a time-suffixed name."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        data = tmp_path / "data"
        data.mkdir()
        artifact = data / "scores.json"

        artifact.write_text("[1]")
        first = rotate_to_legacy(artifact)
        artifact.write_text("[2]")
        second = rotate_to_legacy(artifact)

        assert first is not None and second is not None
        assert first != second
        assert first.read_text() == "[1]"
        assert second.read_text() == "[2]"


class TestWriteWithRotation:
    """Tests for content-aware artifact writes."""

    def test_first_write_rotates_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        path = tmp_path / "data" / "a.json"
        assert write_json_with_rotation(path, {"v": 1}) is None
        assert read_json(path) == {"v": 1}

    def test_identical_content_skips_rotation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regenerating an identical artifact must not spam legacy/."""
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        path = tmp_path / "data" / "a.json"
        write_json_with_rotation(path, {"v": 1})
        assert write_json_with_rotation(path, {"v": 1}) is None
        assert not (tmp_path / "data" / "legacy").exists()

    def test_changed_content_rotates_prior_version(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        path = tmp_path / "data" / "a.json"
        write_json_with_rotation(path, {"v": 1})
        rotated = write_json_with_rotation(path, {"v": 2})

        assert rotated is not None
        assert json.loads(rotated.read_text()) == {"v": 1}
        assert read_json(path) == {"v": 2}

    def test_text_variant_round_trip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_EVAL_BASE_DIR", str(tmp_path))
        path = tmp_path / "data" / "report.html"
        assert write_text_with_rotation(path, "<html>1</html>") is None
        rotated = write_text_with_rotation(path, "<html>2</html>")
        assert rotated is not None
        assert path.read_text() == "<html>2</html>"
