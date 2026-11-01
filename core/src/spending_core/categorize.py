"""Categorization: a scope's own rules first, then the default keywords, then "Other".

A scope is a user (their unshared accounts) or a household (the accounts shared
into it); its rules and category names live in the database. The defaults below
are versioned with the code.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

FALLBACK_CATEGORY = "Other"

DEFAULT_RULES: dict[str, list[str]] = {
    "Groceries": [
        "hemköp", "hemkop", "ica", "coop", "lidl", "willys", "willy",
        "netto", "city gross", "citygross", "maxi", "prisma", "mataffär",
        "bra mat", "saluhall", "matbutik", "snabbköp", "konsum",
    ],
    "Eating out": [
        "restaurang", "restaurant", "pizzeria", "mcdonalds", "mcdonald",
        "burger", "subway", "sushi", "café", "cafe", "bistro", "grill",
        "autogrill", "bar ", "pub ", "7-eleven", "pressbyrån", "pressbyran",
        "max hamburgare", "foodora", "wolt", "pizza", "thai w",
    ],
    "Shopping": [
        "zara", "h&m", "ikea", "apple", "stadium", "elgiganten", "amazon",
        "kappahl", "lindex", "indiska", "asos", "zalando", "boozt",
        "webhallen", "komplett", "mediamarkt", "kicks", "åhléns", "ahléns",
        "nk", "malina", "soft goat",
    ],
    "Transportation": [
        "sl ", "sl\t", "tunnelbana", "sj", "sj ab", "buss",
        "taxi", "uber", "bolt ", "cabify", "vy ", "mtr ", "skytrain",
        "arlanda express", "flygbussarna", "flixbus",
    ],
    "Travel": [
        "hotel", "hotell", "airbnb", "booking.com", "expedia", "hostel",
        "resort", "inn ", "apt ", "apartment", "sas ", "norwegian",
        "ryanair", "easyjet", "wizz", "lufthansa", "british airways",
        "flyg", "airport", "flygplats",
    ],
    "Home/Renovation": [
        "clas", "bauhaus", "byggmax", "byggvaruhus", "byggmaterial", "byggvaror",
        "bygg", "renovering", "renovera", "måla", "färg",
    ],
}

DEFAULT_CATEGORIES: list[str] = [*DEFAULT_RULES, FALLBACK_CATEGORY]

# Monthly targets in SEK used by the Streamlit PoC; the app stores budgets per user or household.
DEFAULT_TARGETS_SEK: dict[str, int] = {
    "Groceries": 5000,
    "Shopping": 5000,
    "Eating out": 2000,
    "Transportation": 2000,
    "Travel": 2000,
    "Home/Renovation": 4000,
    "Other": 4000,
}


def categorize(
    description: str,
    rules: Mapping[str, Sequence[str]] = DEFAULT_RULES,
    fallback: str = FALLBACK_CATEGORY,
) -> str:
    """Return the first category (in rule order) with a keyword contained in the description."""
    text = description.lower()
    for category, keywords in rules.items():
        if any(kw.lower() in text for kw in keywords):
            return category
    return fallback


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass(frozen=True)
class Rule:
    pattern: str  # matched case-insensitively anywhere in the description
    category: str


class Categorizer:
    """Categorize with a scope's own rules, falling back to the default keywords.

    The longest matching pattern wins, so "ICA MAXI BYGG" beats "ICA"; between
    patterns of equal length, the earlier rule wins. `names` maps each default
    category to what the scope calls it (after a rename); a default category the
    scope deleted falls back to the scope's fallback category.
    """

    def __init__(
        self,
        rules: Iterable[Rule] = (),
        names: Mapping[str, str] | None = None,
        defaults: Mapping[str, Sequence[str]] = DEFAULT_RULES,
        fallback: str = FALLBACK_CATEGORY,
    ):
        normalized = [(normalize_text(r.pattern), r.category) for r in rules]
        self.rules = sorted([r for r in normalized if r[0]], key=lambda r: -len(r[0]))
        self.names = names
        self.defaults = defaults
        self.fallback = fallback

    def __call__(self, description: str) -> str:
        text = normalize_text(description)
        for pattern, category in self.rules:
            if pattern in text:
                return category
        default = categorize(description, self.defaults, self.fallback)
        if self.names is None:
            return default
        return self.names.get(default) or self.names.get(self.fallback) or self.fallback
