"""Who-pays-what for a set of transactions shared by N household members.

A member's share = their personal spending + their weight × shared spending.
Outlays (spending to be reimbursed by someone outside the split) are reported
separately, and excluded lines are ignored.
"""

from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Settlement:
    per_member: dict[Hashable, int]  # what each member is responsible for, in minor units
    outlay: int
    shared: int
    total: int  # sum of all non-excluded lines; equals sum(per_member) + outlay


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
    shared = outlay = 0
    for line in lines:
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
    return Settlement(per_member=per_member, outlay=outlay, shared=shared, total=total)


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
