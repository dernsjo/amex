from decimal import Decimal

import pytest

from spending_core import format_minor, parse_amount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("262,71", 26271),
        ("262.71", 26271),
        ("500.0", 50000),
        ("85", 8500),
        ("−123,45", -12345),  # Unicode minus: silently became 0.0 in the old API
        ("-123,45", -12345),
        ("1 234,56", 123456),
        ("1 234,56", 123456),
        ("  12,5 ", 1250),
        ("0,005", 1),  # half up
        (12.3, 1230),
        (7, 700),
        (Decimal("1.10"), 110),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "1,234.56", "nan", "inf", "12,3,4"])
def test_parse_amount_rejects_garbage(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


def test_format_minor_round_trips():
    assert format_minor(-12345) == Decimal("-123.45")
    assert format_minor(5) == Decimal("0.05")


@pytest.mark.parametrize(
    ("raw", "separator", "expected"),
    [
        ("1.234,56", ",", 123456),
        ("-1.234,56", ",", -123456),
        ("1,234.56", ".", 123456),
        ("12,5", ",", 1250),
        ("12.5", ".", 1250),
        ("1 234", ",", 123400),
    ],
)
def test_parse_amount_with_known_separator(raw, separator, expected):
    assert parse_amount(raw, separator) == expected


def test_parse_amount_rejects_unknown_separator():
    with pytest.raises(ValueError, match="Decimal separator"):
        parse_amount("1", ";")
