import pytest

from spending_core import DEFAULT_CATEGORIES, DEFAULT_TARGETS_SEK, Categorizer, Rule, categorize


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


# Categorizer: a scope's own rules on top of the defaults

def test_own_rules_come_before_defaults():
    categorize_ = Categorizer([Rule("ica maxi", "Big shop")])
    assert categorize_("ICA MAXI  NACKA") == "Big shop"  # whitespace and case don't matter
    assert categorize_("ICA NARA ARSTA") == "Groceries"


def test_longest_pattern_wins():
    categorize_ = Categorizer([Rule("ICA", "Groceries"), Rule("ICA MAXI BYGG", "Home/Renovation")])
    assert categorize_("ICA MAXI BYGG STHLM") == "Home/Renovation"


def test_renamed_and_deleted_defaults():
    names = {"Groceries": "Food", "Other": "Misc"}  # Eating out etc. were deleted
    categorize_ = Categorizer(names=names)
    assert categorize_("HEMKOP") == "Food"
    assert categorize_("PIZZERIA") == "Misc"
    assert categorize_("NOTHING") == "Misc"


def test_blank_pattern_never_matches():
    assert Categorizer([Rule("  ", "X")])("anything") == "Other"
