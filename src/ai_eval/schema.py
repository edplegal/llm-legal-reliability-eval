"""Shared domain types and scoring-schema constants for the pipeline.

This module is the single source of truth for the rubric dimensions and the
shapes of the records that flow between pipeline phases. Keeping them here
prevents the drift that occurs when each phase re-declares its own copies.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

DIMENSIONS: list[str] = [
    "disclaimer",
    "escalation",
    "confidence",
    "jurisdiction",
    "guardrail",
    "regulatory",
]

APPLICABLE_DIMENSIONS: list[str] = [
    "disclaimer",
    "escalation",
    "confidence",
    "jurisdiction",
]


class ModelConfig(TypedDict):
    """One model endpoint definition from config.json.

    ``temperature`` is optional and normally absent: the main grid runs at
    provider defaults (current-generation models reject the parameter).
    It exists for methodological side-runs that must replicate historical
    conditions — e.g. the bridge-judging pass, where legacy judges re-run
    at the temperature 0.0 used in the original judging eras.
    """

    provider: str
    model: str
    api_key_env: str
    base_url: str
    temperature: NotRequired[float]


class PromptRecord(TypedDict):
    """One evaluation prompt from prompts.json."""

    id: int
    text: str
    category: str
    domain: NotRequired[str]
    risk_level: NotRequired[str]
    pair_id: NotRequired[str | None]
    pair_role: NotRequired[str | None]


class ProviderResult(TypedDict):
    """Normalized result of one LLM API call, any provider."""

    text: str
    model_version: str
    tokens_used: int


class ResponseRecord(TypedDict):
    """One collected response (Phase 1 output)."""

    prompt_id: int
    model_id: str
    sample_idx: int
    response_text: str
    timestamp: str
    model_version: str
    tokens_used: int
    config_hash: str
    prompts_hash: str


class BlindedResponse(TypedDict):
    """One identity-stripped response shown to judges (Phase 2 output)."""

    prompt_id: int
    response_id: str
    response_text: str


class LookupEntry(TypedDict):
    """Unblinding map entry for one response_id (Phase 2 output)."""

    model_id: str
    prompt_id: int
    sample_idx: int
    timestamp: str


class JudgeScoreRecord(TypedDict):
    """One judgment of one blinded response (Phase 3 output).

    ``scores`` is None when the judge failed to produce parseable JSON after
    retry; these rows surface in the report's tie-breaking section.
    """

    response_id: str
    prompt_id: int
    judge_model: str
    judge_model_version: str | None
    scores: dict[str, Any] | None
    timestamp: str
