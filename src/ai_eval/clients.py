"""Provider API clients shared by the collect and judge phases.

Each caller normalizes one provider's chat API to a :class:`ProviderResult`.
``call_model_with_retry`` adds exponential-backoff retry on top, for callers
that want all-or-nothing semantics (the judge phase layers its own
parse-aware retry instead).

Sampling runs at provider defaults: current-generation models (GPT-5.x,
Claude Sonnet 5) reject explicit ``temperature``/``top_p`` values, so no
sampling parameters are sent to any provider — every model behaves as it
does for a default deployed user. The one exception is an explicit
per-model ``temperature`` in the model's config entry, used by
methodological side-runs (the bridge-judging pass) to replicate the
historical judging conditions on legacy models that still accept it.
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
        max_tokens: int,
    ) -> ProviderResult: ...


def call_openai(
    prompt_text: str,
    model_config: ModelConfig,
    *,
    system_prompt: str,
    max_tokens: int,
) -> ProviderResult:
    """Send a prompt to the OpenAI chat completions API.

    Uses ``max_completion_tokens`` (the universal replacement for
    ``max_tokens``): GPT-5.x models reject the legacy parameter name.
    """
    api_key = os.environ[model_config["api_key_env"]]
    resp = requests.post(
        model_config["base_url"],
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_config["model"],
            "max_completion_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            **(
                {"temperature": model_config["temperature"]}
                if "temperature" in model_config
                else {}
            ),
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
    max_tokens: int,
) -> ProviderResult:
    """Send a prompt to the Anthropic messages API.

    Claude 5-family models run adaptive thinking by default, so the response
    ``content`` list may begin with thinking blocks — the answer is the first
    ``text`` block, not ``content[0]``.
    """
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
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt_text}],
            **(
                {"temperature": model_config["temperature"]}
                if "temperature" in model_config
                else {}
            ),
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    text: str | None = None
    for block in data["content"]:
        if "text" in block and block.get("type", "text") == "text":
            text = block["text"]
            break
    if text is None:
        # Raise KeyError (not StopIteration) so call_model_with_retry's
        # retry net catches it like any other malformed-payload failure.
        raise KeyError(f"no text block in response content: {data['content']!r}")
    return {
        "text": text,
        "model_version": data.get("model", model_config["model"]),
        "tokens_used": data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
    }


def call_google(
    prompt_text: str,
    model_config: ModelConfig,
    *,
    system_prompt: str,
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
                "maxOutputTokens": max_tokens,
                **(
                    {"temperature": model_config["temperature"]}
                    if "temperature" in model_config
                    else {}
                ),
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
                max_tokens=max_tokens,
            )
        except (requests.RequestException, KeyError, IndexError) as exc:
            if attempt == max_retries - 1:
                raise
            wait = min(2 ** (attempt + 1), MAX_RETRY_WAIT)
            logger.warning(
                "Attempt %d/%d for %s failed: %s%s. Retrying in %ds...",
                attempt + 1,
                max_retries,
                model_id,
                exc,
                _http_error_detail(exc),
                wait,
            )
            time.sleep(wait)
    raise RuntimeError("Unreachable")  # pragma: no cover


def _http_error_detail(exc: Exception) -> str:
    """Extract the response body and retry-after from an HTTPError, if any.

    A bare status line ("429 Too Many Requests") cannot distinguish a
    per-minute rate limit from an exhausted quota or budget cap; the JSON
    error body can. Appended to retry warnings so limit failures are
    diagnosable from the log alone.
    """
    if not isinstance(exc, requests.HTTPError) or exc.response is None:
        return ""
    parts: list[str] = []
    retry_after = exc.response.headers.get("retry-after")
    if retry_after:
        parts.append(f"retry-after={retry_after}s")
    body = exc.response.text.strip().replace("\n", " ")
    if body:
        parts.append(f"body: {body[:300]}")
    if not parts:
        return ""
    return " [" + " | ".join(parts) + "]"
