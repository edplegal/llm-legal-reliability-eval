"""Phase 2: Blind responses by stripping model identity and shuffling.

Response IDs are deterministic — a content hash of (prompt_id, model_id,
sample_idx, response_text) — so re-running this phase over the same raw
responses always produces the same IDs. That makes ``judge --resume`` safe
across re-blinds and means judge scores can never be silently orphaned by an
ID reshuffle. Determinism does not weaken the blinding: judges are shown
only the response text, never the ID, and the hash is not invertible without
already knowing the model identity.

If raw responses *have* changed (fresh collection), any existing judge
scores that no longer join to the new lookup are rotated to ``data/legacy/``
rather than left to mis-join downstream.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import random
import re
from typing import TYPE_CHECKING

from ai_eval.paths import (
    data_dir,
    read_json,
    rotate_to_legacy,
    write_json_with_rotation,
)

if TYPE_CHECKING:
    from ai_eval.schema import (
        BlindedResponse,
        JudgeScoreRecord,
        LookupEntry,
        ResponseRecord,
    )

logger = logging.getLogger(__name__)

# Shuffle seed only affects presentation order, never the blinding itself;
# fixed by default so blinded_responses.json is reproducible byte-for-byte.
DEFAULT_SHUFFLE_SEED = 20260522

SELF_ID_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"I'm ChatGPT", re.IGNORECASE),
    re.compile(r"I am ChatGPT", re.IGNORECASE),
    re.compile(r"as ChatGPT", re.IGNORECASE),
    re.compile(r"I'm Claude", re.IGNORECASE),
    re.compile(r"I am Claude", re.IGNORECASE),
    re.compile(r"as Claude", re.IGNORECASE),
    re.compile(r"I'm Gemini", re.IGNORECASE),
    re.compile(r"I am Gemini", re.IGNORECASE),
    re.compile(r"as Gemini", re.IGNORECASE),
    re.compile(r"I'm Bard", re.IGNORECASE),
    re.compile(r"I am Bard", re.IGNORECASE),
    re.compile(r"as an AI language model", re.IGNORECASE),
    re.compile(r"as a large language model", re.IGNORECASE),
    re.compile(r"I'm an AI assistant made by OpenAI", re.IGNORECASE),
    re.compile(r"I'm an AI assistant made by Anthropic", re.IGNORECASE),
    re.compile(r"I'm an AI assistant made by Google", re.IGNORECASE),
    re.compile(r"made by OpenAI", re.IGNORECASE),
    re.compile(r"made by Anthropic", re.IGNORECASE),
    re.compile(r"made by Google", re.IGNORECASE),
    re.compile(r"developed by OpenAI", re.IGNORECASE),
    re.compile(r"developed by Anthropic", re.IGNORECASE),
    re.compile(r"developed by Google", re.IGNORECASE),
    re.compile(r"trained by OpenAI", re.IGNORECASE),
    re.compile(r"trained by Anthropic", re.IGNORECASE),
    re.compile(r"trained by Google", re.IGNORECASE),
    re.compile(r"\bGPT-[345][a-z0-9.\-]*", re.IGNORECASE),
    re.compile(r"\bClaude\s+[34](?:\.\d)?", re.IGNORECASE),
    re.compile(r"\bGemini\s+\d(?:\.\d)?", re.IGNORECASE),
    re.compile(r"OpenAI's", re.IGNORECASE),
    re.compile(r"Anthropic's", re.IGNORECASE),
]


def deterministic_response_id(
    prompt_id: int,
    model_id: str,
    sample_idx: int,
    response_text: str,
) -> str:
    """Derive a stable response ID from the response's identifying content.

    The same raw response always maps to the same ID, so judge scores keyed
    on response_id survive a re-blind. 12 hex chars (48 bits) keeps the
    collision probability negligible at this scale.
    """
    payload = f"{prompt_id}|{model_id}|{sample_idx}|{response_text}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
    return f"R-{digest}"


def scan_for_self_identification(
    response_text: str,
    response_id: str,
    model_id: str,
) -> list[str]:
    """Check response text for self-identification patterns.

    Returns list of matched pattern strings found.
    """
    warnings: list[str] = []
    for pattern in SELF_ID_PATTERNS:
        match = pattern.search(response_text)
        if match:
            msg = (
                f"WARNING: {response_id} (model: {model_id}) "
                f"contains self-identification: '{match.group()}'"
            )
            warnings.append(msg)
    return warnings


def find_orphaned_judge_scores(
    lookup: dict[str, LookupEntry],
) -> list[str]:
    """Return judge-score response_ids that don't join to the given lookup."""
    scores_path = data_dir() / "judge_scores.json"
    if not scores_path.exists():
        return []
    scores: list[JudgeScoreRecord] = read_json(scores_path)
    return sorted({s["response_id"] for s in scores} - set(lookup))


def blind(*, seed: int = DEFAULT_SHUFFLE_SEED) -> None:
    """Run Phase 2: blind and shuffle all collected responses.

    ``seed`` controls only the presentation shuffle of the blinded file.
    Prior differing outputs are rotated to ``data/legacy/``, as are any
    existing judge scores orphaned by changed raw responses.
    """
    raw_path = data_dir() / "raw_responses.json"
    raw_responses: list[ResponseRecord] = read_json(raw_path)

    blinded: list[BlindedResponse] = []
    lookup: dict[str, LookupEntry] = {}
    all_warnings: list[str] = []

    for entry in raw_responses:
        sample_idx = entry.get("sample_idx", 0)
        rid = deterministic_response_id(
            entry["prompt_id"],
            entry["model_id"],
            sample_idx,
            entry["response_text"],
        )
        if rid in lookup:
            raise ValueError(
                f"Duplicate response content for {rid}: "
                f"prompt {entry['prompt_id']}, model {entry['model_id']}, "
                f"sample {sample_idx}. raw_responses.json contains "
                "duplicate entries; deduplicate before blinding."
            )

        blinded.append(
            {
                "prompt_id": entry["prompt_id"],
                "response_id": rid,
                "response_text": entry["response_text"],
            }
        )

        lookup[rid] = {
            "model_id": entry["model_id"],
            "prompt_id": entry["prompt_id"],
            "sample_idx": sample_idx,
            "timestamp": entry["timestamp"],
        }

        all_warnings.extend(
            scan_for_self_identification(entry["response_text"], rid, entry["model_id"])
        )

    random.Random(seed).shuffle(blinded)

    orphaned = find_orphaned_judge_scores(lookup)
    if orphaned:
        scores_path = data_dir() / "judge_scores.json"
        dest = rotate_to_legacy(scores_path)
        logger.warning(
            "%d existing judge scores reference response IDs not present in "
            "the new blind lookup (raw responses changed). Rotated %s -> %s; "
            "re-run `python -m ai_eval.judge`.",
            len(orphaned),
            scores_path.name,
            dest,
        )

    write_json_with_rotation(data_dir() / "blinded_responses.json", blinded)
    write_json_with_rotation(data_dir() / "blind_lookup.json", lookup)

    logger.info("Blinded %d responses.", len(blinded))

    if all_warnings:
        logger.warning("SELF-IDENTIFICATION WARNINGS (%d):", len(all_warnings))
        for w in all_warnings:
            logger.warning("  %s", w)
    else:
        logger.info("No self-identification detected in any response.")


def main() -> None:
    """CLI entry point for Phase 2."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Phase 2: Blind and shuffle collected responses."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SHUFFLE_SEED,
        help=(
            "Shuffle seed for presentation order (fixed default for "
            "reproducible output; IDs are content-derived regardless)."
        ),
    )
    args = parser.parse_args()
    blind(seed=args.seed)


if __name__ == "__main__":
    main()
