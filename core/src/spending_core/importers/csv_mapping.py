"""Generic CSV import: the user says which columns mean what, once per account."""

import re
from dataclasses import asdict, dataclass, fields

from ..errors import ImportFileError
from ..money import parse_amount
from .base import ParsedTransaction, clean_description
from .dates import DATE_FORMATS, guess_date_format, parse_date
from .table import Table


@dataclass(frozen=True)
class CsvMapping:
    date_column: str
    description_column: str
    amount_column: str
    decimal_separator: str = ","  # "," or "."
    # Bank accounts show money going out as negative; we store spending as positive.
    spending_is_negative: bool = True
    date_format: str | None = None  # strptime format; None tries the common ones

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CsvMapping":
        return cls(**{f.name: data[f.name] for f in fields(cls) if f.name in data})


class CsvMappingImporter:
    id = "csv"
    name = "CSV with column mapping"

    def __init__(self, mapping: CsvMapping):
        self.mapping = mapping

    def detect(self, table: Table) -> float:
        m = self.mapping
        return 1.0 if {m.date_column, m.description_column, m.amount_column} <= set(table.header) else 0.0

    def parse(self, table: Table) -> list[ParsedTransaction]:
        m = self.mapping
        date_i, desc_i, amount_i = (table.column(c) for c in (m.date_column, m.description_column, m.amount_column))
        formats = (m.date_format,) if m.date_format else DATE_FORMATS
        sign = -1 if m.spending_is_negative else 1

        transactions = []
        for row in table.rows:
            if not row.cells[date_i]:
                continue  # footers and subtotals ("Summa", "Saldo") have no date
            try:
                booked_on = parse_date(row.cells[date_i], formats)
                amount = parse_amount(row.cells[amount_i], m.decimal_separator)
            except ValueError as e:
                raise ImportFileError(f"Line {row.line}: {e}") from None
            transactions.append(ParsedTransaction(booked_on, clean_description(row.cells[desc_i]), sign * amount))
        return transactions


# Header words banks use, lower-case. Checked in order, so the most specific comes first.
_DATE_NAMES = ("bokföringsdag", "bokföringsdatum", "transaktionsdag", "transaktionsdatum", "datum", "date")
_DESCRIPTION_NAMES = (
    "beskrivning", "text", "specifikation", "rubrik", "meddelande", "mottagare", "referens", "description",
)
_AMOUNT_NAMES = ("belopp", "summa", "amount")
_AMOUNT_RE = re.compile(r"^[-−–+]?[\d  .,]*\d$")


def guess_mapping(table: Table) -> dict:
    """Best guess at a CsvMapping, as a dict where unknown columns are None.

    Names win; otherwise the content decides (dates parse, amounts look numeric,
    the description is the longest text).
    """
    def by_name(names: tuple[str, ...], exclude: set[str]) -> str | None:
        lowered = {h.lower(): h for h in table.header if h not in exclude}
        for name in names:
            for low, original in lowered.items():
                if low == name or low.startswith(name):
                    return original
        return None

    def sample(column: str) -> list[str]:
        return [v for v in table.values(column)[:50] if v]

    used: set[str] = set()
    date_column = by_name(_DATE_NAMES, used) or next(
        (h for h in table.header if sample(h) and guess_date_format(sample(h))), None
    )
    used.add(date_column)
    amount_column = by_name(_AMOUNT_NAMES, used) or next(
        (h for h in table.header if h not in used and sample(h) and all(_AMOUNT_RE.match(v) for v in sample(h))),
        None,
    )
    used.add(amount_column)
    description_column = by_name(_DESCRIPTION_NAMES, used) or max(
        (h for h in table.header if h not in used),
        key=lambda h: sum(len(v) for v in sample(h)),
        default=None,
    )

    amounts = sample(amount_column) if amount_column else []
    return {
        "date_column": date_column,
        "description_column": description_column,
        "amount_column": amount_column,
        "decimal_separator": _guess_decimal_separator(amounts),
        "spending_is_negative": True,
        "date_format": guess_date_format(sample(date_column)) if date_column else None,
    }


def _guess_decimal_separator(amounts: list[str]) -> str:
    """',' unless the amounts use '.' as the last separator (e.g. "1,234.56" or "12.50")."""
    for v in amounts:
        last = max(v.rfind(","), v.rfind("."))
        if last != -1 and len(v) - last - 1 in (1, 2):  # one or two decimals follow it
            return v[last]
    return ","
