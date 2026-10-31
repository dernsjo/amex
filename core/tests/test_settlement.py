from fractions import Fraction

import pytest

from spending_core import Allocation, Line, allocation_from_label, settle

S, P, O, X = Allocation.SHARED, Allocation.PERSONAL, Allocation.OUTLAY, Allocation.EXCLUDED
EVEN = {"Axel": 1, "Ebba": 1}


def test_matches_poc_formula():
    # Reference: calculate_who_pays_what in the Streamlit PoC.
    # shared 1000 + Axel 200 + Ebba 50 + outlay 300, excluded 999
    lines = [
        Line(100000, S),
        Line(20000, P, "Axel"),
        Line(5000, P, "Ebba"),
        Line(30000, O),
        Line(99900, X),
    ]
    result = settle(lines, EVEN)
    assert result.per_member == {"Axel": 70000, "Ebba": 55000}
    assert result.outlay == 30000
    assert result.shared == 100000
    assert result.total == 155000


def test_old_api_bug_split_is_not_a_person():
    # The old API returned {"Split": +400, "Axel": -400} for this input.
    result = settle([Line(100000, S), Line(20000, P, "Axel")], EVEN)
    assert result.per_member == {"Axel": 70000, "Ebba": 50000}


def test_odd_ore_reconciles():
    result = settle([Line(101, S)], {"A": 1, "B": 1, "C": 1})
    assert sorted(result.per_member.values()) == [33, 34, 34]
    assert sum(result.per_member.values()) == 101


def test_negative_shared_refund_reconciles():
    result = settle([Line(-101, S)], EVEN)
    assert sum(result.per_member.values()) == -101


def test_weighted_split():
    result = settle([Line(100000, S)], {"A": Fraction(3, 5), "B": Fraction(2, 5)})
    assert result.per_member == {"A": 60000, "B": 40000}


def test_member_with_no_lines_still_gets_shared_part():
    result = settle([Line(300, S)], {"A": 1, "B": 1, "C": 1})
    assert result.per_member == {"A": 100, "B": 100, "C": 100}


def test_unknown_member_is_rejected():
    with pytest.raises(ValueError, match="unknown member"):
        settle([Line(100, P, "Ghost")], EVEN)


@pytest.mark.parametrize("weights", [{}, {"A": 0}, {"A": -1, "B": 2}])
def test_invalid_weights(weights):
    with pytest.raises(ValueError):
        settle([], weights)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Delad", (S, None)),
        ("Split", (S, None)),
        ("Utlägg", (O, None)),
        ("Outlay", (O, None)),
        ("Excludera", (X, None)),
        ("Exclude", (X, None)),
        ("Ebba", (P, "Ebba")),
    ],
)
def test_allocation_from_label(label, expected):
    assert allocation_from_label(label, EVEN) == expected


def test_unknown_label():
    with pytest.raises(ValueError, match="Unknown paid-by label"):
        allocation_from_label("Nobody", EVEN)
