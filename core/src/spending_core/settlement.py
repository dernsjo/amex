"""Who-pays-what for a set of transactions shared by N household members.

A member's share = their personal spending + their weight × shared spending.
Outlays (spending to be reimbursed by someone outside the split) are reported
separately, and excluded lines are ignored.

When lines say who paid them, each member's balance is what they paid minus
their share, and `settle_up` turns the balances into transfers ("B pays A 120 kr").
"""

from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction


class Allocation(StrEnum):
    SHARED = "shared"
    PERSONAL = "personal"
    OUTLAY = "outlay"
    EXCLUDED = "excluded"


# Labels used by the Streamlit PoC (Swedish) and the current API (English).
_LABELS = {
    "delad": Allocation.SHARED,
    "split": Allocation.SHARED,
    "utlägg": Allocation.OUTLAY,
    "outlay": Allocation.OUTLAY,
    "excludera": Allocation.EXCLUDED,
    "exclude": Allocation.EXCLUDED,
}


@dataclass(frozen=True)
class Line:
    amount_minor: int
    allocation: Allocation
    member: Hashable | None = None  # a name or id; required iff allocation is PERSONAL
    payer: Hashable | None = None  # the member whose card or account paid, if known


@dataclass(frozen=True)
class Settlement:
    per_member: dict[Hashable, int]  # what each member is responsible for, in minor units
    outlay: int
    shared: int
    total: int  # sum of all non-excluded lines; equals sum(per_member) + outlay
    # What each member paid of the shared and personal lines (outlays are settled outside the split).
    paid: dict[Hashable, int] = field(default_factory=dict)

    @property
    def balances(self) -> dict[Hashable, int]:
        """Paid minus share: positive is owed money, negative owes."""
        return {m: self.paid.get(m, 0) - share for m, share in self.per_member.items()}


@dataclass(frozen=True)
class Transfer:
    debtor: Hashable
    creditor: Hashable
    amount: int


def allocation_from_label(label: str, members: Iterable[str]) -> tuple[Allocation, str | None]:
    """Map a legacy 'paid by' label to (allocation, member).

    A label matching a member name means a personal expense for that member.
    """
    members = list(members)
    if label in members:
        return Allocation.PERSONAL, label
    try:
        return _LABELS[label.strip().lower()], None
    except KeyError:
        raise ValueError(f"Unknown paid-by label {label!r}; expected a member or one of {sorted(_LABELS)}") from None


def settle(lines: Iterable[Line], weights: Mapping[Hashable, int | Fraction]) -> Settlement:
    """Split lines between members according to weights (e.g. {"A": 1, "B": 1} for 50/50).

    Shared amounts are split exactly in minor units: leftover öre from rounding go
    to the members with the largest remainders, so totals always reconcile.
    """
    if not weights:
        raise ValueError("At least one member is required")
    if any(w < 0 for w in weights.values()) or sum(weights.values()) == 0:
        raise ValueError("Weights must be non-negative and not all zero")

    personal = dict.fromkeys(weights, 0)
    paid = dict.fromkeys(weights, 0)
    shared = outlay = 0
    for line in lines:
        if line.allocation in (Allocation.SHARED, Allocation.PERSONAL) and line.payer is not None:
            if line.payer not in paid:
                raise ValueError(f"Line paid by unknown member {line.payer!r}")
            paid[line.payer] += line.amount_minor
        match line.allocation:
            case Allocation.EXCLUDED:
                continue
            case Allocation.SHARED:
                shared += line.amount_minor
            case Allocation.OUTLAY:
                outlay += line.amount_minor
            case Allocation.PERSONAL:
                if line.member not in personal:
                    raise ValueError(f"Personal line for unknown member {line.member!r}")
                personal[line.member] += line.amount_minor

    shares = _split_exact(shared, weights)
    per_member = {m: personal[m] + shares[m] for m in weights}
    total = sum(per_member.values()) + outlay
    return Settlement(per_member=per_member, outlay=outlay, shared=shared, total=total, paid=paid)


def settle_up(balances: Mapping[Hashable, int]) -> list[Transfer]:
    """The transfers that bring every balance to zero, at most one fewer than the members.

    The largest debtor pays the largest creditor first. Balances must add up to
    zero, which they do when every shared and personal line says who paid it.
    """
    if sum(balances.values()) != 0:
        raise ValueError("Balances must add up to zero; does every line say who paid it?")
    # Sorted is stable, so ties keep the members' order and results are deterministic.
    debtors = [[m, -b] for m, b in sorted(balances.items(), key=lambda kv: kv[1]) if b < 0]
    creditors = [[m, b] for m, b in sorted(balances.items(), key=lambda kv: -kv[1]) if b > 0]
    transfers = []
    while debtors and creditors:
        (debtor, owes), (creditor, owed) = debtors[0], creditors[0]
        amount = min(owes, owed)
        transfers.append(Transfer(debtor, creditor, amount))
        debtors[0][1] -= amount
        creditors[0][1] -= amount
        if debtors[0][1] == 0:
            debtors.pop(0)
        if creditors[0][1] == 0:
            creditors.pop(0)
    return transfers


def _split_exact(amount: int, weights: Mapping[Hashable, int | Fraction]) -> dict[Hashable, int]:
    """Largest-remainder apportionment of an integer amount; handles negative amounts."""
    sign = -1 if amount < 0 else 1
    amount = abs(amount)
    total_weight = Fraction(sum(weights.values()))
    exact = {m: Fraction(amount) * Fraction(w) / total_weight for m, w in weights.items()}
    floors = {m: int(v) for m, v in exact.items()}
    leftover = amount - sum(floors.values())
    # Ties broken by insertion order, so results are deterministic.
    order = sorted(weights, key=lambda m: exact[m] - floors[m], reverse=True)
    for m in order[:leftover]:
        floors[m] += 1
    return {m: sign * v for m, v in floors.items()}


def settle_by_category(
    lines: Iterable[tuple[Hashable, Line]], weights: Mapping[Hashable, int | Fraction]
) -> dict[Hashable, Settlement]:
    """`settle` per category, e.g. to compare each member's share of groceries with a budget.

    Any hashable key works, such as (month, category) for trends.
    """
    grouped: dict[Hashable, list[Line]] = {}
    for category, line in lines:
        grouped.setdefault(category, []).append(line)
    return {category: settle(group, weights) for category, group in grouped.items()}
