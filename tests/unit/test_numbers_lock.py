"""Tests for the numbers-lock helpers."""

from __future__ import annotations

import pytest

from ai_eval.numbers_lock import ceil_hundredth, fmt, normalize, word


class TestHelpers:
    """Formatting and normalization used to match document text."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(-0.659, "-0.66"), (0.0, "+0.00"), (1.07, "+1.07")],
    )
    def test_fmt_signed_two_decimals(self, value: float, expected: str) -> None:
        assert fmt(value) == expected

    def test_normalize_collapses_whitespace_and_minus(self) -> None:
        assert normalize("a  \n b −0.5") == "a b -0.5"

    @pytest.mark.parametrize(
        ("value", "expected"), [(0.019, 0.02), (0.044, 0.05), (0.02, 0.03)]
    )
    def test_ceil_hundredth_next_hundredth(self, value: float, expected: float) -> None:
        assert ceil_hundredth(value) == pytest.approx(expected)

    def test_word_known_and_fallback(self) -> None:
        assert word(25, True) == "Twenty-five"
        assert word(14) == "fourteen"
        assert word(37) == "37"
