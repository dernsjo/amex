from collections.abc import Iterable
from datetime import date, datetime

# Tried in this order when guessing. Day-first comes before month-first because
# that's what Swedish and European banks use; Amex's month-first export has its own importer.
DATE_FORMATS = ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y")


def parse_date(raw: str, formats: Iterable[str] = DATE_FORMATS) -> date:
    text = (raw or "").strip()
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date {raw!r}")


def guess_date_format(values: Iterable[str]) -> str | None:
    """The first format that parses every non-empty value, or None."""
    values = [v.strip() for v in values if v and v.strip()]
    if not values:
        return None
    for fmt in DATE_FORMATS:
        try:
            for v in values:
                datetime.strptime(v, fmt)
        except ValueError:
            continue
        return fmt
    return None
