"""Importer for American Express (Sweden) CSV exports."""

from ..errors import ImportFileError
from ..money import parse_amount
from .base import ParsedTransaction, clean_description
from .dates import parse_date
from .table import Table, read_table

REQUIRED_COLUMNS = ("Datum", "Beskrivning", "Belopp")
# ISO first; then month-first, which is how pandas.to_datetime read these files in the PoC.
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y")


class AmexSE:
    id = "amex_se"
    name = "American Express (Sweden)"

    def detect(self, table: Table) -> float:
        found = sum(c in table.header for c in REQUIRED_COLUMNS)
        if found < len(REQUIRED_COLUMNS):
            return 0.0
        # Other Swedish exports also say Datum/Belopp; Amex's are exactly these plus optional extras.
        return 1.0 if table.header[: len(REQUIRED_COLUMNS)] == list(REQUIRED_COLUMNS) else 0.8

    def parse(self, table: Table) -> list[ParsedTransaction]:
        missing = [c for c in REQUIRED_COLUMNS if c not in table.header]
        if missing:
            raise ImportFileError(f"Not an Amex export: missing column(s) {', '.join(missing)}")
        date_i, desc_i, amount_i = (table.column(c) for c in REQUIRED_COLUMNS)

        transactions = []
        for row in table.rows:
            try:
                transactions.append(
                    ParsedTransaction(
                        booked_on=parse_date(row.cells[date_i], DATE_FORMATS),
                        description=clean_description(row.cells[desc_i]),
                        amount_minor=parse_amount(row.cells[amount_i]),  # charges are positive
                    )
                )
            except ValueError as e:
                raise ImportFileError(f"Line {row.line}: {e}") from None
        return transactions


def parse_amex_csv(content: str | bytes) -> list[ParsedTransaction]:
    """Parse an Amex CSV export. Raises ImportFileError naming the offending row."""
    return AmexSE().parse(read_table(content))
