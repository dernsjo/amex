"""Stable fingerprints for imported transactions, so re-uploading a file adds nothing."""

import hashlib
from collections import Counter
from collections.abc import Iterable

from .importers import ParsedTransaction


def normalize_description(description: str) -> str:
    return " ".join(description.lower().split())


def dedupe_hashes(account_key: str | int, transactions: Iterable[ParsedTransaction]) -> list[str]:
    """One hash per transaction, in order.

    Identical rows in one file (two coffees, same day, same price) are told apart
    by how many times the combination has appeared so far, so an overlapping
    re-export still lines up with what was imported before.
    """
    seen: Counter[tuple] = Counter()
    hashes = []
    for t in transactions:
        key = (str(account_key), t.booked_on.isoformat(), t.amount_minor, normalize_description(t.description))
        occurrence = seen[key]
        seen[key] += 1
        hashes.append(hashlib.sha256("|".join(map(str, (*key, occurrence))).encode()).hexdigest())
    return hashes
