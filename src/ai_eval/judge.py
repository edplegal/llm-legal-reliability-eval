"""Phase 3: Have each model judge every blinded response using the rubric."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

JUDGE_SYSTEM_PROMPT = "You are an expert evaluator. Respond with only valid JSON."


def load_config() -> dict[str, Any]:
    """Load pipeline configuration from config.json."""
    config_path = BASE_DIR / "config.json"
    with config_path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def load_judge_template() -> str:
    """Load the judge prompt template."""
    template_path = BASE_DIR / "judge_prompt_template.txt"
    with template_path.open() as f:
        return f.read()


def load_blinded_responses() -> list[dict[str, Any]]:
    """Load blinded responses from Phase 2 output."""
    path = DATA_DIR / "blinded_responses.json"
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def load_prompts_by_id() -> dict[int, dict[str, Any]]:
    """Load prompts indexed by ID."""
    prompts_path = BASE_DIR / "prompts.json"
    with prompts_path.open() as f:
        data = json.load(f)
    return {p["id"]: p for p in data["prompts"]}


def build_judge_prompt(
    template: str, prompt_text: str, response_text: str
) -> str:
    """Inject prompt and response into the judge template."""
    return template.replace("{prompt_text}", prompt_text).replace(
        "{response_text}", response_text
    )


def call_judge_openai(
    judge_prompt: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Call OpenAI as a judge. Returns {text, model_version}."""
    api_key = os.environ[model_config["api_key_env"]]
    resp = requests.post(
        model_config["base_url"],
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_config["model"],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": judge_prompt},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["choices"][0]["message"]["content"],
        "model_version": data.get("model", model_config["model"]),
    }


def call_judge_anthropic(
    judge_prompt: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Call Anthropic as a judge. Returns {text, model_version}."""
    api_key = os.environ[model_config["api_key_env"]]
    resp = requests.post(
        model_config["base_url"],
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": model_config["model"],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": JUDGE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": judge_prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["content"][0]["text"],
        "model_version": data.get("model", model_config["model"]),
    }


def call_judge_google(
    judge_prompt: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Call Google Gemini as a judge. Returns {text, model_version}."""
    api_key = os.environ[model_config["api_key_env"]]
    model_name = model_config["model"]
    url = f"{model_config['base_url']}/{model_name}:generateContent?key={api_key}"
    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": judge_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "systemInstruction": {"parts": [{"text": JUDGE_SYSTEM_PROMPT}]},
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["candidates"][0]["content"]["parts"][0]["text"],
        "model_version": data.get("modelVersion", model_name),
    }


JUDGE_CALLERS = {
    "openai": call_judge_openai,
    "anthropic": call_judge_anthropic,
    "google": call_judge_google,
}


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


def call_judge_with_retry(
    judge_prompt: str,
    model_id: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> tuple[dict[str, Any] | None, str | None]:
    """Call a judge model and parse its JSON response, retrying once on failure.

    Returns (parsed_scores, model_version). The model_version captures the
    actual model snapshot returned by the API (e.g., 'gpt-4o-2024-08-06')
    so analysis_results.json carries reproducibility metadata.
    """
    caller = JUDGE_CALLERS[model_config["provider"]]
    last_model_version: str | None = None
    for attempt in range(2):
        try:
            result = caller(
                judge_prompt, model_config, temperature, max_tokens
            )
            last_model_version = result.get("model_version")
            return extract_json(result["text"]), last_model_version
        except (
            requests.RequestException,
            KeyError,
            IndexError,
            ValueError,
        ) as exc:
            if attempt == 0:
                logger.warning(
                    "Judge call to %s failed (attempt 1): %s. Retrying...",
                    model_id,
                    exc,
                )
                time.sleep(2)
            else:
                logger.error(
                    "Judge call to %s failed (attempt 2): %s. Storing null.",
                    model_id,
                    exc,
                )
                return None, last_model_version
    return None, last_model_version  # pragma: no cover


def load_existing_scores(output_path: Path) -> list[dict[str, Any]]:
    """Load existing judge scores for resume support."""
    if output_path.exists():
        with output_path.open() as f:
            return json.load(f)  # type: ignore[no-any-return]
    return []


def get_completed_judge_keys(
    scores: list[dict[str, Any]],
) -> set[tuple[str, str]]:
    """Extract (response_id, judge_model) pairs from existing scores."""
    return {(s["response_id"], s["judge_model"]) for s in scores}


def judge(
    *,
    resume: bool = False,
    dry_run: bool = False,
) -> None:
    """Run Phase 3: have all models judge all blinded responses."""
    config = load_config()
    template = load_judge_template()
    blinded = load_blinded_responses()
    prompts_by_id = load_prompts_by_id()
    models = config["models"]
    temperature = config["judge_temperature"]
    max_tokens = config["judge_max_tokens"]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "judge_scores.json"

    scores: list[dict[str, Any]] = []
    completed: set[tuple[str, str]] = set()

    if resume:
        scores = load_existing_scores(output_path)
        completed = get_completed_judge_keys(scores)
        logger.info("Resuming: %d judge scores already collected.", len(completed))

    total_calls = len(blinded) * len(models)
    call_num = 0

    for response_entry in blinded:
        response_id: str = response_entry["response_id"]
        prompt_id: int = response_entry["prompt_id"]
        response_text: str = response_entry["response_text"]
        prompt_text: str = prompts_by_id[prompt_id]["text"]

        judge_prompt = build_judge_prompt(template, prompt_text, response_text)

        for model_id, model_config in models.items():
            call_num += 1

            if (response_id, model_id) in completed:
                print(
                    f"[{call_num}/{total_calls}] Judging {response_id}"
                    f" with {model_id}... skipped (already judged)"
                )
                continue

            if dry_run:
                print(
                    f"[{call_num}/{total_calls}] Judging {response_id}"
                    f" with {model_id}... DRY RUN"
                )
                continue

            print(
                f"[{call_num}/{total_calls}] Judging {response_id}"
                f" with {model_id}...",
                end=" ",
                flush=True,
            )

            parsed, judge_model_version = call_judge_with_retry(
                judge_prompt,
                model_id,
                model_config,
                temperature,
                max_tokens,
            )

            entry: dict[str, Any] = {
                "response_id": response_id,
                "prompt_id": prompt_id,
                "judge_model": model_id,
                "judge_model_version": judge_model_version,
                "scores": parsed,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            scores.append(entry)

            with output_path.open("w") as f:
                json.dump(scores, f, indent=2)

            status = "done" if parsed is not None else "FAILED (null scores)"
            print(status)

            time.sleep(2)

    if not dry_run:
        print(
            f"\nJudging complete. {len(scores)} scores saved to {output_path}"
        )


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
