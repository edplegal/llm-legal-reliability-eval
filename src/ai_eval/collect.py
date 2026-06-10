"""Phase 1: Collect responses from configured LLM APIs for each prompt."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ai_eval.clients import PROVIDER_CALLERS, call_model_with_retry
from ai_eval.paths import (
    data_dir,
    load_config,
    load_prompts,
    prompts_file_hash,
    rotate_to_legacy,
    write_json_atomic,
)

if TYPE_CHECKING:
    from pathlib import Path

    from ai_eval.schema import ResponseRecord

__all__ = [
    "PROVIDER_CALLERS",
    "call_model_with_retry",
    "collect",
    "config_hash",
    "get_completed_keys",
    "load_existing_responses",
    "main",
]

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a helpful assistant."
RATE_LIMIT_SLEEP = 2.0


def config_hash(config: dict[str, Any], samples: int) -> str:
    """Stable hash over the config + sample count for reproducibility metadata."""
    payload = json.dumps(
        {
            "models": {
                k: {kk: vv for kk, vv in v.items() if kk != "api_key_env"}
                for k, v in config.get("models", {}).items()
            },
            "response_temperature": config.get("response_temperature"),
            "response_max_tokens": config.get("response_max_tokens"),
            "system_prompt": SYSTEM_PROMPT,
            "samples_per_cell": samples,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def load_existing_responses(output_path: Path) -> list[ResponseRecord]:
    """Load existing responses, normalizing sample_idx for older files."""
    if not output_path.exists():
        return []
    with output_path.open() as f:
        data: list[ResponseRecord] = json.load(f)
    for entry in data:
        entry.setdefault("sample_idx", 0)
    return data


def get_completed_keys(
    responses: list[ResponseRecord],
) -> set[tuple[int, str, int]]:
    """Extract (prompt_id, model_id, sample_idx) tuples from responses."""
    return {(r["prompt_id"], r["model_id"], r.get("sample_idx", 0)) for r in responses}


def collect(
    *,
    resume: bool = False,
    dry_run: bool = False,
    samples: int = 1,
) -> None:
    """Run Phase 1: collect responses from all models for all prompts.

    With ``samples > 1``, each (prompt, model) cell is queried that many times
    so downstream analysis can separate response variance from judge variance.

    A fresh (non-resume) run rotates any existing raw_responses.json to
    ``data/legacy/`` before writing — outputs are never silently overwritten.
    """
    if samples < 1:
        raise ValueError("samples must be >= 1")

    config = load_config()
    prompts = load_prompts()
    models = config["models"]
    temperature: float = config["response_temperature"]
    max_tokens: int = config["response_max_tokens"]
    cfg_hash = config_hash(config, samples)
    prompts_h = prompts_file_hash()

    output_path = data_dir() / "raw_responses.json"

    responses: list[ResponseRecord] = []
    completed: set[tuple[int, str, int]] = set()

    if resume:
        responses = load_existing_responses(output_path)
        completed = get_completed_keys(responses)
        logger.info("Resuming: %d responses already collected.", len(completed))
    elif not dry_run:
        rotate_to_legacy(output_path)

    total_calls = len(prompts) * len(models) * samples
    call_num = 0

    for prompt in prompts:
        prompt_id = prompt["id"]
        prompt_text = prompt["text"]

        for model_id, model_config in models.items():
            for sample_idx in range(samples):
                call_num += 1
                label = (
                    f"[{call_num}/{total_calls}] Prompt {prompt_id}"
                    f" -> {model_id}#{sample_idx}"
                )

                if (prompt_id, model_id, sample_idx) in completed:
                    logger.info("%s: skipped (already collected)", label)
                    continue

                if dry_run:
                    logger.info("%s: DRY RUN", label)
                    continue

                result = call_model_with_retry(
                    prompt_text,
                    model_id,
                    model_config,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                entry: ResponseRecord = {
                    "prompt_id": prompt_id,
                    "model_id": model_id,
                    "sample_idx": sample_idx,
                    "response_text": result["text"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "model_version": result["model_version"],
                    "tokens_used": result["tokens_used"],
                    "config_hash": cfg_hash,
                    "prompts_hash": prompts_h,
                }
                responses.append(entry)
                write_json_atomic(output_path, responses)

                logger.info("%s: done (%d tokens)", label, result["tokens_used"])
                time.sleep(RATE_LIMIT_SLEEP)

    if not dry_run:
        logger.info(
            "Collection complete. %d responses saved to %s",
            len(responses),
            output_path,
        )


def main() -> None:
    """CLI entry point for Phase 1."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Phase 1: Collect LLM responses for evaluation prompts."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip (prompt, model, sample) tuples already in the output file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making API calls.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help=(
            "Number of independent samples per (prompt, model) cell. "
            "Defaults to 1 for backward compatibility; use 3+ to separate "
            "response variance from judge variance."
        ),
    )
    args = parser.parse_args()

    collect(resume=args.resume, dry_run=args.dry_run, samples=args.samples)


if __name__ == "__main__":
    main()
