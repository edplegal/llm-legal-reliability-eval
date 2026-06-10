"""Tests for Phase 2: blind module."""

from __future__ import annotations

from ai_eval.blind import generate_response_id, scan_for_self_identification


class TestGenerateResponseId:
    """Tests for random ID generation."""

    def test_format_matches_pattern(self) -> None:
        """Generated ID follows R-XXXXX format."""
        rid = generate_response_id(set())
        assert rid.startswith("R-")
        assert len(rid) == 7
        assert rid[2:].isalnum()

    def test_uniqueness(self) -> None:
        """Generated IDs are unique across calls."""
        existing: set[str] = set()
        for _ in range(100):
            rid = generate_response_id(existing)
            assert rid not in existing
            existing.add(rid)

    def test_avoids_existing_ids(self) -> None:
        """New ID is not in the existing set."""
        existing = {"R-aaaaa", "R-bbbbb"}
        rid = generate_response_id(existing)
        assert rid not in existing


class TestScanForSelfIdentification:
    """Tests for self-identification detection."""

    def test_detects_chatgpt_self_id(self) -> None:
        """Catches 'I'm ChatGPT' pattern."""
        warnings = scan_for_self_identification(
            "I'm ChatGPT and I can help you.", "R-test1", "chatgpt"
        )
        assert len(warnings) >= 1
        assert "ChatGPT" in warnings[0]

    def test_detects_claude_self_id(self) -> None:
        """Catches 'I'm Claude' pattern."""
        warnings = scan_for_self_identification(
            "As Claude, I should note...", "R-test2", "claude"
        )
        assert len(warnings) >= 1
        assert "Claude" in warnings[0]

    def test_detects_ai_language_model(self) -> None:
        """Catches 'as an AI language model' pattern."""
        warnings = scan_for_self_identification(
            "As an AI language model, I cannot provide legal advice.",
            "R-test3",
            "gemini",
        )
        assert len(warnings) >= 1

    def test_no_false_positives(self) -> None:
        """Clean text produces no warnings."""
        warnings = scan_for_self_identification(
            "You should consult an attorney about this matter.",
            "R-clean",
            "chatgpt",
        )
        assert len(warnings) == 0

    def test_detects_made_by_pattern(self) -> None:
        """Catches 'made by OpenAI' pattern."""
        warnings = scan_for_self_identification(
            "I was made by OpenAI.", "R-test4", "chatgpt"
        )
        assert len(warnings) >= 1

    def test_case_insensitive(self) -> None:
        """Detection is case-insensitive."""
        warnings = scan_for_self_identification(
            "i'm chatgpt", "R-test5", "chatgpt"
        )
        assert len(warnings) >= 1
