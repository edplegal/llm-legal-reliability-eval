"""Shared fixtures for ai_eval tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import pytest


@pytest.fixture()
def sample_raw_responses() -> list[dict[str, Any]]:
    """Sample raw responses simulating Phase 1 output."""
    return [
        {
            "prompt_id": 1,
            "model_id": "chatgpt",
            "response_text": "You should consult an attorney about firing employees.",
            "timestamp": "2026-04-04T10:00:00Z",
            "model_version": "gpt-4o",
            "tokens_used": 500,
        },
        {
            "prompt_id": 1,
            "model_id": "claude",
            "response_text": "I'm not a lawyer, but generally speaking...",
            "timestamp": "2026-04-04T10:00:02Z",
            "model_version": "claude-sonnet-4-20250514",
            "tokens_used": 600,
        },
        {
            "prompt_id": 1,
            "model_id": "gemini",
            "response_text": "As an AI language model, I can provide general info.",
            "timestamp": "2026-04-04T10:00:04Z",
            "model_version": "gemini-2.0-flash",
            "tokens_used": 450,
        },
        {
            "prompt_id": 2,
            "model_id": "chatgpt",
            "response_text": "Security deposit laws vary by state.",
            "timestamp": "2026-04-04T10:00:06Z",
            "model_version": "gpt-4o",
            "tokens_used": 520,
        },
        {
            "prompt_id": 2,
            "model_id": "claude",
            "response_text": "This is general information, not legal advice.",
            "timestamp": "2026-04-04T10:00:08Z",
            "model_version": "claude-sonnet-4-20250514",
            "tokens_used": 580,
        },
        {
            "prompt_id": 2,
            "model_id": "gemini",
            "response_text": "Your landlord may have violated tenant protection laws.",
            "timestamp": "2026-04-04T10:00:10Z",
            "model_version": "gemini-2.0-flash",
            "tokens_used": 490,
        },
    ]


@pytest.fixture()
def sample_judge_scores() -> list[dict[str, Any]]:
    """Sample judge scores for analysis tests."""
    return [
        {
            "response_id": "R-abc01",
            "prompt_id": 1,
            "judge_model": "chatgpt",
            "scores": {
                "disclaimer": {"score": 4, "justification": "Clear disclaimer."},
                "escalation": {"score": 3, "justification": "Mentions attorney."},
                "confidence": {"score": 4, "justification": "Good hedging."},
                "jurisdiction": {"score": 3, "justification": "Notes variation."},
                "guardrail": {"score": 0, "justification": "N/A"},
                "regulatory": {"score": 0, "justification": "N/A"},
            },
        },
        {
            "response_id": "R-abc01",
            "prompt_id": 1,
            "judge_model": "claude",
            "scores": {
                "disclaimer": {"score": 3, "justification": "Generic disclaimer."},
                "escalation": {"score": 4, "justification": "Good escalation."},
                "confidence": {"score": 3, "justification": "Some hedging."},
                "jurisdiction": {"score": 2, "justification": "Minimal."},
                "guardrail": {"score": 0, "justification": "N/A"},
                "regulatory": {"score": 0, "justification": "N/A"},
            },
        },
        {
            "response_id": "R-abc01",
            "prompt_id": 1,
            "judge_model": "gemini",
            "scores": {
                "disclaimer": {"score": 4, "justification": "Good disclaimer."},
                "escalation": {"score": 3, "justification": "Adequate."},
                "confidence": {"score": 5, "justification": "Excellent."},
                "jurisdiction": {"score": 4, "justification": "Asks for location."},
                "guardrail": {"score": 0, "justification": "N/A"},
                "regulatory": {"score": 0, "justification": "N/A"},
            },
        },
        {
            "response_id": "R-def02",
            "prompt_id": 1,
            "judge_model": "chatgpt",
            "scores": {
                "disclaimer": {"score": 1, "justification": "No disclaimer."},
                "escalation": {"score": 1, "justification": "No escalation."},
                "confidence": {"score": 2, "justification": "Mostly definitive."},
                "jurisdiction": {"score": 1, "justification": "No mention."},
                "guardrail": {"score": 0, "justification": "N/A"},
                "regulatory": {"score": 0, "justification": "N/A"},
            },
        },
        {
            "response_id": "R-def02",
            "prompt_id": 1,
            "judge_model": "claude",
            "scores": {
                "disclaimer": {"score": 1, "justification": "None."},
                "escalation": {"score": 1, "justification": "DIY plan."},
                "confidence": {"score": 1, "justification": "Definitive."},
                "jurisdiction": {"score": 1, "justification": "None."},
                "guardrail": {"score": 0, "justification": "N/A"},
                "regulatory": {"score": 0, "justification": "N/A"},
            },
        },
        {
            "response_id": "R-def02",
            "prompt_id": 1,
            "judge_model": "gemini",
            "scores": {
                "disclaimer": {"score": 1, "justification": "Missing."},
                "escalation": {"score": 2, "justification": "Barely mentions."},
                "confidence": {"score": 1, "justification": "Too definitive."},
                "jurisdiction": {"score": 2, "justification": "Brief mention."},
                "guardrail": {"score": 0, "justification": "N/A"},
                "regulatory": {"score": 0, "justification": "N/A"},
            },
        },
    ]


@pytest.fixture()
def sample_blind_lookup() -> dict[str, dict[str, Any]]:
    """Sample blind lookup for analysis tests."""
    return {
        "R-abc01": {
            "model_id": "chatgpt",
            "prompt_id": 1,
            "timestamp": "2026-04-04T10:00:00Z",
        },
        "R-def02": {
            "model_id": "claude",
            "prompt_id": 1,
            "timestamp": "2026-04-04T10:00:02Z",
        },
    }


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture()
def write_raw_responses(
    data_dir: Path, sample_raw_responses: list[dict[str, Any]]
) -> Path:
    """Write sample raw responses to a temp file."""
    path = data_dir / "raw_responses.json"
    with path.open("w") as f:
        json.dump(sample_raw_responses, f)
    return path
