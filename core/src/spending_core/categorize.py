"""Keyword-based categorization.

These defaults move to database rules (global + per household) in Phase 3;
`categorize` already takes the rules as a parameter so that is a drop-in change.
"""

from collections.abc import Mapping, Sequence

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

# Monthly targets in SEK. Become per-household Budget rows in Phase 3.
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
