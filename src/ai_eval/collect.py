"""Phase 1: Collect responses from configured LLM APIs for each prompt."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

SYSTEM_PROMPT = "You are a helpful assistant."


def load_config() -> dict[str, Any]:
    """Load pipeline configuration from config.json."""
    config_path = BASE_DIR / "config.json"
    with config_path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def load_prompts() -> list[dict[str, Any]]:
    """Load evaluation prompts from prompts.json."""
    prompts_path = BASE_DIR / "prompts.json"
    with prompts_path.open() as f:
        data = json.load(f)
    return data["prompts"]  # type: ignore[no-any-return]


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


def prompts_hash() -> str:
    """Stable hash of the current prompts.json content.

    Stamped on every collected response so the analyzer can detect when
    data was gathered against a different prompt set than the one
    currently on disk. Cheaper and more reliable than text-similarity
    heuristics.
    """
    prompts_path = BASE_DIR / "prompts.json"
    with prompts_path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def call_openai(
    prompt_text: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Send a prompt to the OpenAI API and return response data."""
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
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_text},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "response_text": data["choices"][0]["message"]["content"],
        "model_version": data.get("model", model_config["model"]),
        "tokens_used": data["usage"]["total_tokens"],
    }


def call_anthropic(
    prompt_text: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Send a prompt to the Anthropic API and return response data."""
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
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt_text}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "response_text": data["content"][0]["text"],
        "model_version": data.get("model", model_config["model"]),
        "tokens_used": data["usage"]["input_tokens"]
        + data["usage"]["output_tokens"],
    }


def call_google(
    prompt_text: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Send a prompt to the Google Gemini API and return response data."""
    api_key = os.environ[model_config["api_key_env"]]
    model_name = model_config["model"]
    url = f"{model_config['base_url']}/{model_name}:generateContent?key={api_key}"
    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "response_text": data["candidates"][0]["content"]["parts"][0]["text"],
        "model_version": data.get("modelVersion", model_name),
        "tokens_used": data.get("usageMetadata", {}).get(
            "totalTokenCount", 0
        ),
    }


PROVIDER_CALLERS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "google": call_google,
}


def call_model_with_retry(
    prompt_text: str,
    model_id: str,
    model_config: dict[str, Any],
    temperature: float,
    max_tokens: int,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Call a model API with exponential backoff retry logic."""
    caller = PROVIDER_CALLERS[model_config["provider"]]
    for attempt in range(max_retries):
        try:
            return caller(prompt_text, model_config, temperature, max_tokens)
        except (requests.RequestException, KeyError, IndexError) as exc:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            logger.warning(
                "Attempt %d/%d for %s failed: %s. Retrying in %ds...",
                attempt + 1,
                max_retries,
                model_id,
                exc,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError("Unreachable")  # pragma: no cover


def load_existing_responses(output_path: Path) -> list[dict[str, Any]]:
    """Load existing responses, normalizing sample_idx for older files."""
    if not output_path.exists():
        return []
    with output_path.open() as f:
        data: list[dict[str, Any]] = json.load(f)
    for entry in data:
        entry.setdefault("sample_idx", 0)
    return data


def get_completed_keys(
    responses: list[dict[str, Any]],
) -> set[tuple[int, str, int]]:
    """Extract (prompt_id, model_id, sample_idx) tuples from responses."""
    return {
        (r["prompt_id"], r["model_id"], r.get("sample_idx", 0))
        for r in responses
    }


def collect(
    *,
    resume: bool = False,
    dry_run: bool = False,
    samples: int = 1,
) -> None:
    """Run Phase 1: collect responses from all models for all prompts.

    With ``samples > 1``, each (prompt, model) cell is queried that many times
    so downstream analysis can separate response variance from judge variance.
    """
    if samples < 1:
        raise ValueError("samples must be >= 1")

    config = load_config()
    prompts = load_prompts()
    models = config["models"]
    temperature = config["response_temperature"]
    max_tokens = config["response_max_tokens"]
    cfg_hash = config_hash(config, samples)
    prompts_h = prompts_hash()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "raw_responses.json"

    responses: list[dict[str, Any]] = []
    completed: set[tuple[int, str, int]] = set()

    if resume:
        responses = load_existing_responses(output_path)
        completed = get_completed_keys(responses)
        logger.info(
            "Resuming: %d responses already collected.", len(completed)
        )

    total_calls = len(prompts) * len(models) * samples
    call_num = 0

    for prompt in prompts:
        prompt_id: int = prompt["id"]
        prompt_text: str = prompt["text"]

        for model_id, model_config in models.items():
            for sample_idx in range(samples):
                call_num += 1

                if (prompt_id, model_id, sample_idx) in completed:
                    print(
                        f"[{call_num}/{total_calls}] Prompt {prompt_id}"
                        f" -> {model_id}#{sample_idx}..."
                        " skipped (already collected)"
                    )
                    continue

                if dry_run:
                    print(
                        f"[{call_num}/{total_calls}] Prompt {prompt_id}"
                        f" -> {model_id}#{sample_idx}... DRY RUN"
                    )
                    continue

                print(
                    f"[{call_num}/{total_calls}] Prompt {prompt_id}"
                    f" -> {model_id}#{sample_idx}...",
                    end=" ",
                    flush=True,
                )

                result = call_model_with_retry(
                    prompt_text,
                    model_id,
                    model_config,
                    temperature,
                    max_tokens,
                )

                entry = {
                    "prompt_id": prompt_id,
                    "model_id": model_id,
                    "sample_idx": sample_idx,
                    "response_text": result["response_text"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "model_version": result["model_version"],
                    "tokens_used": result["tokens_used"],
                    "config_hash": cfg_hash,
                    "prompts_hash": prompts_h,
                }
                responses.append(entry)

                with output_path.open("w") as f:
                    json.dump(responses, f, indent=2)

                print(f"done ({result['tokens_used']} tokens)")

                time.sleep(2)

    if not dry_run:
        print(
            f"\nCollection complete. {len(responses)} responses"
            f" saved to {output_path}"
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
