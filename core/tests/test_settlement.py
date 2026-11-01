from fractions import Fraction

import pytest

from spending_core import Allocation, Line, Transfer, allocation_from_label, settle, settle_by_category, settle_up

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


def test_settle_by_category():
    lines = [
        ("Groceries", Line(1001, Allocation.SHARED)),
        ("Groceries", Line(500, Allocation.PERSONAL, "B")),
        ("Travel", Line(300, Allocation.SHARED)),
    ]
    result = settle_by_category(lines, {"A": 1, "B": 1})
    assert result["Groceries"].per_member == {"A": 501, "B": 1000}
    assert result["Groceries"].shared == 1001
    assert result["Travel"].per_member == {"A": 150, "B": 150}


# Who paid, and who owes whom


def test_balances_from_who_paid():
    # Axel's card paid everything; Ebba's personal 50 and half the shared 1000 are hers.
    lines = [
        Line(100000, S, payer="Axel"),
        Line(20000, P, "Axel", payer="Axel"),
        Line(5000, P, "Ebba", payer="Axel"),
        Line(30000, O, payer="Axel"),  # settled with whoever is outside the split
        Line(99900, X, payer="Axel"),
    ]
    result = settle(lines, EVEN)
    assert result.paid == {"Axel": 125000, "Ebba": 0}
    assert result.balances == {"Axel": 55000, "Ebba": -55000}
    assert settle_up(result.balances) == [Transfer("Ebba", "Axel", 55000)]


def test_both_paid_and_weights():
    lines = [Line(60000, S, payer="A"), Line(40000, S, payer="B")]
    result = settle(lines, {"A": 1, "B": 3})
    assert result.balances == {"A": 35000, "B": -35000}


def test_settle_up_three_members():
    balances = {"A": 9000, "B": -6000, "C": -3000}
    assert settle_up(balances) == [Transfer("B", "A", 6000), Transfer("C", "A", 3000)]
    balances = {"A": 5000, "B": 1000, "C": -6000}
    assert settle_up(balances) == [Transfer("C", "A", 5000), Transfer("C", "B", 1000)]


def test_settle_up_when_even():
    assert settle_up({"A": 0, "B": 0}) == []


def test_settle_up_needs_balanced_input():
    with pytest.raises(ValueError, match="add up to zero"):
        settle_up({"A": 100, "B": 0})


def test_unknown_payer():
    with pytest.raises(ValueError, match="unknown member"):
        settle([Line(100, S, payer="Ghost")], EVEN)
