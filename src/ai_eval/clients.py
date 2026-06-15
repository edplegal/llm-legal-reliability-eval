"""Provider API clients shared by the collect and judge phases.

Each caller normalizes one provider's chat API to a :class:`ProviderResult`.
``call_model_with_retry`` adds exponential-backoff retry on top, for callers
that want all-or-nothing semantics (the judge phase layers its own
parse-aware retry instead).
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Protocol

import requests

if TYPE_CHECKING:
    from ai_eval.schema import ModelConfig, ProviderResult

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 120


class ProviderCaller(Protocol):
    """Signature shared by all provider callers."""

    def __call__(
        self,
        prompt_text: str,
        model_config: ModelConfig,
        *,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> ProviderResult: ...


def call_openai(
    prompt_text: str,
    model_config: ModelConfig,
    *,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> ProviderResult:
    """Send a prompt to the OpenAI chat completions API."""
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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text},
            ],
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["choices"][0]["message"]["content"],
        "model_version": data.get("model", model_config["model"]),
        "tokens_used": data["usage"]["total_tokens"],
    }


def call_anthropic(
    prompt_text: str,
    model_config: ModelConfig,
    *,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> ProviderResult:
    """Send a prompt to the Anthropic messages API."""
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
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt_text}],
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["content"][0]["text"],
        "model_version": data.get("model", model_config["model"]),
        "tokens_used": data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
    }


def call_google(
    prompt_text: str,
    model_config: ModelConfig,
    *,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
) -> ProviderResult:
    """Send a prompt to the Google Gemini generateContent API.

    The API key travels in the ``x-goog-api-key`` header, never the URL, so
    it cannot leak into proxy or server logs.
    """
    api_key = os.environ[model_config["api_key_env"]]
    model_name = model_config["model"]
    url = f"{model_config['base_url']}/{model_name}:generateContent"
    resp = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        json={
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "systemInstruction": {"parts": [{"text": system_prompt}]},
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["candidates"][0]["content"]["parts"][0]["text"],
        "model_version": data.get("modelVersion", model_name),
        "tokens_used": data.get("usageMetadata", {}).get("totalTokenCount", 0),
    }


PROVIDER_CALLERS: dict[str, ProviderCaller] = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "google": call_google,
}


MAX_RETRY_WAIT = 60


def call_model_with_retry(
    prompt_text: str,
    model_id: str,
    model_config: ModelConfig,
    *,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
    max_retries: int = 5,
) -> ProviderResult:
    """Call a model API with exponential-backoff retry.

    Waits 2, 4, 8, 16... seconds (capped at MAX_RETRY_WAIT) between
    attempts — enough to ride out transient 429/5xx weather like an
    overloaded Gemini endpoint. Raises the final exception if every
    attempt fails; callers decide whether that is fatal (the collect
    phase skips the cell and continues).
    """
    caller = PROVIDER_CALLERS[model_config["provider"]]
    for attempt in range(max_retries):
        try:
            return caller(
                prompt_text,
                model_config,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except (requests.RequestException, KeyError, IndexError) as exc:
            if attempt == max_retries - 1:
                raise
            wait = min(2 ** (attempt + 1), MAX_RETRY_WAIT)
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
