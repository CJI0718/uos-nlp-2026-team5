"""calculate_comparison: the whitelisted arithmetic behind several of the 50 cases.

General-purpose research agents leave this to the model's mental arithmetic.
These are the cases where that fails:
- FC001  price difference and percent increase
- FC002  PST -> KST offset
- FC020  parameter-count unit notation
"""

from __future__ import annotations

import pytest

from task_a.schema import ToolStatus
from task_a.tools import calculate_comparison, check_url


def test_fc001_price_difference():
    """2,127,400 - 1,962,400 = 165,000 KRW."""
    result = calculate_comparison("diff", a=2_127_400, b=1_962_400)

    assert result.status == ToolStatus.OK
    assert result.payload["value"] == 165_000


def test_fc001_percent_increase_uses_previous_price_as_denominator():
    """165,000 / 1,962,400 = 8.4081% -> the article's 8.4% is correct.

    evaluation.md FC001 states '약 8.407%'. The exact quotient is 8.40807...%,
    so the third decimal in the gold rationale is off by one. It still rounds to
    8.4%, so the reference verdict is unaffected, but the scorer must compare
    the computed value rather than the string in the rationale.
    """
    result = calculate_comparison("pct_change", old=1_962_400, new=2_127_400)

    assert result.status == ToolStatus.OK
    assert result.payload["value"] == pytest.approx(8.40807, abs=0.0001)
    assert result.payload["absolute_change"] == 165_000
    assert round(result.payload["value"], 1) == 8.4


def test_percent_change_rejects_zero_denominator():
    result = calculate_comparison("pct_change", old=0, new=100)

    assert result.status == ToolStatus.INVALID_INPUT
    assert "0 분모" in result.observation


def test_percentage_point_is_labelled_differently_from_percent():
    """%p is a gap between two rates, never a relative change."""
    result = calculate_comparison("percentage_point_gap", a=80.0, b=50.0)

    assert result.status == ToolStatus.OK
    assert result.payload["value"] == 30.0
    assert result.payload["unit"] == "%p"
    assert "%p" in result.observation


def test_fc002_pst_to_kst_is_plus_seventeen_hours():
    result = calculate_comparison("tz_convert", time="2024-01-19 05:00",
                                  from_tz="PST", to_tz="KST")

    assert result.status == ToolStatus.OK
    assert result.payload["offset_hours"] == 17
    assert result.payload["value"] == "2024-01-19 22:00"


def test_tz_convert_crosses_midnight():
    """05:00 PST on Jan 19 is 22:00 KST the same day; 09:00 PST rolls over."""
    result = calculate_comparison("tz_convert", time="2024-01-19 09:00",
                                  from_tz="PST", to_tz="KST")

    assert result.payload["value"] == "2024-01-20 02:00"


def test_korean_time_meridiem_is_parsed():
    result = calculate_comparison("tz_convert", time="2024-01-19 오전 05:00",
                                  from_tz="PST", to_tz="KST")

    assert result.status == ToolStatus.OK
    assert result.payload["value"] == "2024-01-19 22:00"


def test_korean_pm_is_not_read_as_am():
    """Regression: '오후 05:00' must become 17:00, not 05:00."""
    result = calculate_comparison("tz_convert", time="2024-01-19 오후 05:00",
                                  from_tz="KST", to_tz="UTC")

    assert result.status == ToolStatus.OK
    assert result.payload["value"] == "2024-01-19 08:00"


def test_unknown_timezone_is_rejected_not_guessed():
    result = calculate_comparison("tz_convert", time="2024-01-19 05:00",
                                  from_tz="XYZ", to_tz="KST")

    assert result.status == ToolStatus.INVALID_INPUT


def test_fc020_billion_to_million_unit_scale():
    """Llama 3.1 405B: 405 billion = 405,000 million."""
    result = calculate_comparison("scale_unit", value=405, from_unit="billion", to_unit="million")

    assert result.status == ToolStatus.OK
    assert result.payload["value"] == 405_000


def test_korean_counting_units():
    result = calculate_comparison("scale_unit", value=1, from_unit="억", to_unit="만")

    assert result.payload["value"] == 10_000


def test_unsupported_unit_pair_is_rejected():
    result = calculate_comparison("scale_unit", value=1, from_unit="lightyear", to_unit="parsec")

    assert result.status == ToolStatus.INVALID_INPUT


def test_unknown_operation_is_rejected():
    result = calculate_comparison("__import__('os').system('ls')")

    assert result.status == ToolStatus.INVALID_INPUT
    assert "허용되지 않은 연산" in result.observation


def test_missing_argument_is_invalid_input():
    assert calculate_comparison("diff", a=1).status == ToolStatus.INVALID_INPUT


@pytest.mark.parametrize("url,allowed,should_block", [
    ("https://www.apple.com/newsroom/", None, False),
    ("https://ubuntu.com/security/CVE-2026-98432", None, False),
    ("https://sub.example.com/x", frozenset({"example.com"}), False),
    ("https://evil.com/x", frozenset({"example.com"}), True),
    ("https://example.com.evil.com/x", frozenset({"example.com"}), True),
    ("file:///etc/passwd", None, True),
    ("javascript:alert(1)", None, True),
    ("http://localhost/x", None, True),
    ("http://localhost.localdomain/x", None, True),
    # Regression: urlsplit strips the brackets, so a regex on '[::1]' never matched.
    ("http://[::1]/x", None, True),
    ("http://[fe80::1]/x", None, True),
    ("http://[fc00::1]/x", None, True),
    ("http://10.0.0.5/x", None, True),
    ("http://172.16.0.1/x", None, True),
    ("http://169.254.169.254/latest/meta-data", None, True),
    ("http://0.0.0.0/x", None, True),
    ("http://metadata.google.internal/x", None, True),
])
def test_check_url(url, allowed, should_block):
    assert (check_url(url, allowed) is not None) == should_block
