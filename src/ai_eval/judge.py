"""Phase 3: Have each model judge every blinded response using the rubric."""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import requests

from ai_eval.clients import call_model_with_retry
from ai_eval.paths import (
    base_dir,
    data_dir,
    load_config,
    load_prompts_by_id,
    read_json,
    rotate_to_legacy,
    write_json_atomic,
)
from ai_eval.schema import DIMENSIONS

if TYPE_CHECKING:
    from pathlib import Path

    from ai_eval.schema import BlindedResponse, JudgeScoreRecord, ModelConfig

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = "You are an expert evaluator. Respond with only valid JSON."
RATE_LIMIT_SLEEP = 2.0


def load_judge_template() -> str:
    """Load the judge prompt template."""
    with (base_dir() / "judge_prompt_template.txt").open() as f:
        return f.read()


def load_blinded_responses() -> list[BlindedResponse]:
    """Load blinded responses from Phase 2 output."""
    return read_json(data_dir() / "blinded_responses.json")  # type: ignore[no-any-return]


def build_judge_prompt(template: str, prompt_text: str, response_text: str) -> str:
    """Inject prompt and response into the judge template."""
    return template.replace("{prompt_text}", prompt_text).replace(
        "{response_text}", response_text
    )


def extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from a response that may contain markdown fences or preamble."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {text[:200]}")


def validate_scores(parsed: dict[str, Any]) -> dict[str, Any]:
    """Ensure judge JSON matches the rubric shape before it enters the data.

    Every dimension present must be an object carrying an integer ``score``
    in 0..5 (0 = N/A). Raises ValueError otherwise, so a wrong-shaped answer
    is re-asked exactly like syntactically invalid JSON. Motivation: in the
    first gen-5 run, Sonnet 5 emitted 4/1080 partially flat responses
    (e.g. ``"guardrail": 3`` instead of an object) — real scores in the
    wrong shape, which crashed analysis downstream.
    """
    for dim in DIMENSIONS:
        value = parsed.get(dim)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError(
                f"dimension {dim!r} is {type(value).__name__}, "
                "expected an object with a 'score' field"
            )
        score = value.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 5:
            raise ValueError(f"dimension {dim!r} score is {score!r}, expected int 0..5")
    return parsed


def call_judge_with_retry(
    judge_prompt: str,
    model_id: str,
    model_config: ModelConfig,
    max_tokens: int,
    *,
    parse_attempts: int = 2,
) -> tuple[dict[str, Any] | None, str | None]:
    """Call a judge model and parse its JSON response.

    Transport failures (timeouts, 429/5xx weather like an overloaded Gemini
    endpoint) are absorbed by :func:`call_model_with_retry`'s exponential
    backoff, so a flaky provider no longer drops a judgment on the first
    hiccup. Layered on top, a call that succeeds but returns unparseable JSON
    is re-asked up to ``parse_attempts`` times — judges sample at provider
    defaults, so JSON validity is not deterministic.

    Returns ``(parsed_scores, model_version)``. ``model_version`` captures the
    actual snapshot the API returned (e.g. 'gpt-4o-2024-08-06') so
    analysis_results.json carries reproducibility metadata. Returns
    ``(None, last_model_version)`` if the API never succeeds or every parse
    attempt fails — the caller stores null scores, which surface in the
    report's tie-breaking section.
    """
    last_model_version: str | None = None
    for attempt in range(parse_attempts):
        try:
            result = call_model_with_retry(
                judge_prompt,
                model_id,
                model_config,
                system_prompt=JUDGE_SYSTEM_PROMPT,
                max_tokens=max_tokens,
            )
        except (requests.RequestException, KeyError, IndexError) as exc:
            logger.error(
                "Judge call to %s failed after retries: %s. Storing null.",
                model_id,
                exc,
            )
            return None, last_model_version
        last_model_version = result["model_version"]
        try:
            return validate_scores(extract_json(result["text"])), last_model_version
        except ValueError as exc:
            if attempt == parse_attempts - 1:
                logger.error(
                    "Judge %s returned unparseable JSON after %d attempt(s): "
                    "%s. Storing null.",
                    model_id,
                    parse_attempts,
                    exc,
                )
                return None, last_model_version
            logger.warning(
                "Judge %s returned unparseable JSON (attempt %d/%d): %s. "
                "Re-asking...",
                model_id,
                attempt + 1,
                parse_attempts,
                exc,
            )
    return None, last_model_version  # pragma: no cover


def load_existing_scores(output_path: Path) -> list[JudgeScoreRecord]:
    """Load existing judge scores for resume support."""
    if output_path.exists():
        return read_json(output_path)  # type: ignore[no-any-return]
    return []


def get_completed_judge_keys(
    scores: list[JudgeScoreRecord],
) -> set[tuple[str, str]]:
    """Extract (response_id, judge_model) pairs from existing scores."""
    return {(s["response_id"], s["judge_model"]) for s in scores}


def judge(
    *,
    resume: bool = False,
    dry_run: bool = False,
) -> None:
    """Run Phase 3: have all models judge all blinded responses.

    A fresh (non-resume) run rotates any existing judge_scores.json to
    ``data/legacy/`` before writing — outputs are never silently overwritten.
    """
    config = load_config()
    template = load_judge_template()
    blinded = load_blinded_responses()
    prompts_by_id = load_prompts_by_id()
    models = config["models"]
    max_tokens: int = config["judge_max_tokens"]

    output_path = data_dir() / "judge_scores.json"

    scores: list[JudgeScoreRecord] = []
    completed: set[tuple[str, str]] = set()

    if resume:
        scores = load_existing_scores(output_path)
        completed = get_completed_judge_keys(scores)
        logger.info("Resuming: %d judge scores already collected.", len(completed))
    elif not dry_run:
        rotate_to_legacy(output_path)

    total_calls = len(blinded) * len(models)
    call_num = 0

    for response_entry in blinded:
        response_id = response_entry["response_id"]
        prompt_id = response_entry["prompt_id"]
        response_text = response_entry["response_text"]
        prompt_text = prompts_by_id[prompt_id]["text"]

        judge_prompt = build_judge_prompt(template, prompt_text, response_text)

        for model_id, model_config in models.items():
            call_num += 1
            label = (
                f"[{call_num}/{total_calls}] Judging {response_id}" f" with {model_id}"
            )

            if (response_id, model_id) in completed:
                logger.info("%s: skipped (already judged)", label)
                continue

            if dry_run:
                logger.info("%s: DRY RUN", label)
                continue

            parsed, judge_model_version = call_judge_with_retry(
                judge_prompt,
                model_id,
                model_config,
                max_tokens,
            )

            entry: JudgeScoreRecord = {
                "response_id": response_id,
                "prompt_id": prompt_id,
                "judge_model": model_id,
                "judge_model_version": judge_model_version,
                "scores": parsed,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            scores.append(entry)
            write_json_atomic(output_path, scores)

            logger.info(
                "%s: %s",
                label,
                "done" if parsed is not None else "FAILED (null scores)",
            )
            time.sleep(RATE_LIMIT_SLEEP)

    if not dry_run:
        logger.info("Judging complete. %d scores saved to %s", len(scores), output_path)


def main() -> None:
    """CLI entry point for Phase 3."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Phase 3: Judge blinded responses with all models."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip response/judge pairs already scored.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making API calls.",
    )
    args = parser.parse_args()

    judge(resume=args.resume, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
