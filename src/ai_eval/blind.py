"""Phase 2: Blind responses by stripping model identity and shuffling."""

from __future__ import annotations

import json
import logging
import random
import re
import string
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

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
    re.compile(r"as an AI language model", re.IGNORECASE),
    re.compile(r"I'm an AI assistant made by OpenAI", re.IGNORECASE),
    re.compile(r"I'm an AI assistant made by Anthropic", re.IGNORECASE),
    re.compile(r"I'm an AI assistant made by Google", re.IGNORECASE),
    re.compile(r"made by OpenAI", re.IGNORECASE),
    re.compile(r"made by Anthropic", re.IGNORECASE),
    re.compile(r"made by Google", re.IGNORECASE),
]


def generate_response_id(existing_ids: set[str]) -> str:
    """Generate a unique random 6-character alphanumeric response ID."""
    while True:
        chars = string.ascii_lowercase + string.digits
        suffix = "".join(random.choices(chars, k=5))
        rid = f"R-{suffix}"
        if rid not in existing_ids:
            return rid


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


def blind(*, seed: int | None = None) -> None:
    """Run Phase 2: blind and shuffle all collected responses."""
    if seed is not None:
        random.seed(seed)

    raw_path = DATA_DIR / "raw_responses.json"
    with raw_path.open() as f:
        raw_responses: list[dict[str, Any]] = json.load(f)

    existing_ids: set[str] = set()
    blinded: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    all_warnings: list[str] = []

    for entry in raw_responses:
        rid = generate_response_id(existing_ids)
        existing_ids.add(rid)

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
            "timestamp": entry["timestamp"],
        }

        warnings = scan_for_self_identification(
            entry["response_text"],
            rid,
            entry["model_id"],
        )
        all_warnings.extend(warnings)

    random.shuffle(blinded)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    blinded_path = DATA_DIR / "blinded_responses.json"
    with blinded_path.open("w") as f:
        json.dump(blinded, f, indent=2)

    lookup_path = DATA_DIR / "blind_lookup.json"
    with lookup_path.open("w") as f:
        json.dump(lookup, f, indent=2)

    print(f"Blinded {len(blinded)} responses -> {blinded_path}")
    print(f"Lookup table -> {lookup_path}")

    if all_warnings:
        print(f"\n{'='*60}")
        print(f"SELF-IDENTIFICATION WARNINGS ({len(all_warnings)}):")
        print(f"{'='*60}")
        for w in all_warnings:
            print(f"  {w}")
            logger.warning(w)
    else:
        print("\nNo self-identification detected in any response.")


def main() -> None:
    """CLI entry point for Phase 2."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    blind()


if __name__ == "__main__":
    main()
