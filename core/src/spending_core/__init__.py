"""Domain logic shared by the API and the Streamlit PoC.

Nothing in this package may import FastAPI, SQLAlchemy, Streamlit or pandas.
Amounts are always integer minor units (öre) to avoid float rounding.
"""

from .amex import ParsedTransaction, parse_amex_csv
from .categorize import DEFAULT_CATEGORIES, DEFAULT_TARGETS_SEK, categorize
from .errors import ImportFileError
from .money import format_minor, parse_amount, to_minor
from .settlement import Allocation, Line, Settlement, allocation_from_label, settle

__all__ = [
    "Allocation",
    "DEFAULT_CATEGORIES",
    "DEFAULT_TARGETS_SEK",
    "ImportFileError",
    "Line",
    "ParsedTransaction",
    "Settlement",
    "allocation_from_label",
    "categorize",
    "format_minor",
    "parse_amex_csv",
    "parse_amount",
    "settle",
    "to_minor",
]
