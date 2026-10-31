import pytest

from spending_core import DEFAULT_CATEGORIES, DEFAULT_TARGETS_SEK, categorize


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("HEMKOP SABIS STOCKHO 09 STOCKHOLM", "Groceries"),
        ("BRA MAT 89 DANDERYD", "Groceries"),
        ("7133 AUTOGRILL PALERMO CINISI", "Eating out"),
        ("BAUHAUS BARKARBY", "Home/Renovation"),  # keyword was "BAUHAUS" and never matched
        ("PERIODENS DEL AV ÅRSAVGIFT FÖR KONTOT", "Other"),
    ],
)
def test_default_rules(description, expected):
    assert categorize(description) == expected


def test_first_matching_rule_wins():
    rules = {"A": ["foo"], "B": ["foo bar"]}
    assert categorize("FOO BAR", rules) == "A"


def test_custom_fallback():
    assert categorize("nothing", {"A": ["x"]}, fallback="Uncategorized") == "Uncategorized"


def test_every_category_has_a_target():
    assert set(DEFAULT_TARGETS_SEK) == set(DEFAULT_CATEGORIES)
