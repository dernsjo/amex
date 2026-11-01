"""Domain logic shared by the API and the Streamlit PoC.

Nothing in this package may import FastAPI, SQLAlchemy, Streamlit or pandas.
Amounts are always integer minor units (öre) to avoid float rounding.
"""

from .categorize import DEFAULT_CATEGORIES, DEFAULT_TARGETS_SEK, categorize
from .dedupe import dedupe_hashes, normalize_description
from .errors import ImportFileError
from .importers import (
    BUILTIN_IMPORTERS,
    CsvMapping,
    ImportConfig,
    Importer,
    ParsedTransaction,
    Table,
    importer_for,
    parse_amex_csv,
    read_table,
    resolve,
)
from .money import format_minor, parse_amount, to_minor
from .settlement import Allocation, Line, Settlement, allocation_from_label, settle

__all__ = [
    "Allocation",
    "BUILTIN_IMPORTERS",
    "CsvMapping",
    "DEFAULT_CATEGORIES",
    "DEFAULT_TARGETS_SEK",
    "ImportConfig",
    "ImportFileError",
    "Importer",
    "Line",
    "ParsedTransaction",
    "Settlement",
    "Table",
    "allocation_from_label",
    "categorize",
    "dedupe_hashes",
    "format_minor",
    "importer_for",
    "normalize_description",
    "parse_amex_csv",
    "parse_amount",
    "read_table",
    "resolve",
    "settle",
    "to_minor",
]
