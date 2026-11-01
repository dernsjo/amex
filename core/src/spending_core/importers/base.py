from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .table import Table


@dataclass(frozen=True)
class ParsedTransaction:
    booked_on: date
    description: str
    amount_minor: int  # positive = spending, negative = refund/payment/income


class Importer(Protocol):
    id: str
    name: str

    def detect(self, table: Table) -> float:
        """Confidence 0–1 that this importer understands the file."""
        ...

    def parse(self, table: Table) -> list[ParsedTransaction]:
        """Raises ImportFileError naming the offending line."""
        ...


def clean_description(raw: str) -> str:
    return " ".join((raw or "").split())
