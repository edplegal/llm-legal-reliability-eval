"""Path resolution and provenance-safe JSON file IO.

All pipeline phases resolve paths through this module so that:

- tests (and alternate deployments) can relocate the project root via the
  ``AI_EVAL_BASE_DIR`` environment variable;
- no artifact is ever silently overwritten — regenerating a file moves the
  prior version to ``data/legacy/`` with a date suffix first;
- incremental saves are atomic (write to a temp file, then rename), so an
  interrupted run can never truncate an output file.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_eval.schema import PromptRecord

logger = logging.getLogger(__name__)

BASE_DIR_ENV = "AI_EVAL_BASE_DIR"
GENERATED_AT_ENV = "AI_EVAL_GENERATED_AT"


def base_dir() -> Path:
    """Project root: ``AI_EVAL_BASE_DIR`` if set, else the repo checkout."""
    env = os.environ.get(BASE_DIR_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent


def data_dir() -> Path:
    """Pipeline output directory."""
    return base_dir() / "data"


def legacy_dir() -> Path:
    """Superseded-artifact directory."""
    return data_dir() / "legacy"


def archive_dir() -> Path:
    """Earlier judged runs that the generational analysis consumes."""
    return data_dir() / "archive"


def generated_at_stamp() -> str:
    """Timestamp written into analysis outputs.

    ``AI_EVAL_GENERATED_AT`` overrides the clock so that a re-run can
    reproduce a committed output byte for byte; ``reproduce.py`` passes the
    committed file's own stamp. Without the override, the current UTC time.
    """
    env = os.environ.get(GENERATED_AT_ENV)
    if env:
        return env
    return datetime.now(UTC).isoformat()


def load_config() -> dict[str, Any]:
    """Load pipeline configuration from config.json at the project root."""
    with (base_dir() / "config.json").open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def load_prompts() -> list[PromptRecord]:
    """Load evaluation prompts from prompts.json at the project root."""
    with (base_dir() / "prompts.json").open() as f:
        data = json.load(f)
    return data["prompts"]  # type: ignore[no-any-return]


def load_prompts_by_id() -> dict[int, PromptRecord]:
    """Load prompts indexed by ID."""
    return {p["id"]: p for p in load_prompts()}


def load_prompt_metadata() -> dict[int, dict[str, Any]]:
    """Prompts indexed by ID as plain dicts, for the analysis-side modules."""
    return {pid: dict(record) for pid, record in load_prompts_by_id().items()}


def prompts_file_hash() -> str:
    """Stable hash of the current prompts.json content.

    Stamped on every collected response so downstream phases can detect when
    data was gathered against a different prompt set than the one currently
    on disk. Cheaper and more reliable than text-similarity heuristics.
    """
    with (base_dir() / "prompts.json").open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def read_json(path: Path) -> Any:
    """Read a JSON file."""
    with path.open() as f:
        return json.load(f)


def write_json_atomic(path: Path, obj: Any) -> None:
    """Write JSON via a temp file + rename so a crash can't truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def rotate_to_legacy(path: Path) -> Path | None:
    """Move an existing artifact to legacy/ with a date suffix.

    Returns the destination path, or None if ``path`` does not exist. The
    destination never collides: a same-day rotation gets a time suffix.
    Callers (or the human running the pipeline) must record the rotation in
    the INVENTORY.md of both folders in the same commit.
    """
    if not path.exists():
        return None
    legacy = legacy_dir()
    legacy.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    dest = legacy / f"{path.stem}_{now:%Y-%m-%d}{path.suffix}"
    if dest.exists():
        dest = legacy / f"{path.stem}_{now:%Y-%m-%d_%H%M%S}{path.suffix}"
    path.rename(dest)
    logger.warning(
        "Rotated %s -> %s. Update data/INVENTORY.md and "
        "data/legacy/INVENTORY.md in the same commit.",
        path.name,
        dest.relative_to(data_dir()),
    )
    return dest


def write_text_with_rotation(path: Path, content: str) -> Path | None:
    """Write a text artifact, rotating any differing prior version to legacy.

    If the existing file already holds exactly the content about to be
    written, nothing happens (no rotation, no rewrite) — regenerating an
    identical artifact carries no provenance information.

    Returns the legacy path of the rotated prior version, if any.
    """
    if path.exists() and path.read_text() == content:
        logger.info("%s unchanged; skipping write.", path.name)
        return None
    rotated = rotate_to_legacy(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)
    return rotated


def write_json_with_rotation(path: Path, obj: Any) -> Path | None:
    """JSON form of :func:`write_text_with_rotation`."""
    return write_text_with_rotation(path, json.dumps(obj, indent=2))
