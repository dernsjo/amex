"""Importer for American Express (Sweden) CSV exports."""

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from .errors import ImportFileError
from .money import parse_amount

REQUIRED_COLUMNS = ("Datum", "Beskrivning", "Belopp")
# ISO first; then month-first, which is how pandas.to_datetime read these files in the PoC.
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y")


@dataclass(frozen=True)
class ParsedTransaction:
    booked_on: date
    description: str
    amount_minor: int  # positive = charge, negative = refund/payment


def parse_amex_csv(content: str | bytes) -> list[ParsedTransaction]:
    """Parse an Amex CSV export. Raises ImportFileError naming the offending row."""
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ImportFileError("File is not UTF-8 encoded") from None
    content = content.lstrip("﻿")

    reader = csv.DictReader(io.StringIO(content))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ImportFileError(f"Not an Amex export: missing column(s) {', '.join(missing)}")

    transactions = []
    # Row 1 is the header, so data starts at line 2.
    for line_no, row in enumerate(reader, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue
        try:
            transactions.append(
                ParsedTransaction(
                    booked_on=_parse_date(row["Datum"]),
                    description=" ".join((row["Beskrivning"] or "").split()),
                    amount_minor=parse_amount(row["Belopp"] or ""),
                )
            )
        except ValueError as e:
            raise ImportFileError(f"Line {line_no}: {e}") from None
    return transactions


def _parse_date(raw: str) -> date:
    text = (raw or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date {raw!r}")
