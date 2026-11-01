"""Bank file importers and how one is chosen for an upload."""

from dataclasses import dataclass

from ..errors import ImportFileError
from .amex import AmexSE, parse_amex_csv
from .base import Importer, ParsedTransaction
from .csv_mapping import CsvMapping, CsvMappingImporter, guess_mapping
from .table import Row, Table, read_table

BUILTIN_IMPORTERS: tuple[Importer, ...] = (AmexSE(),)
# Below this a built-in importer isn't trusted to pick itself.
AUTO_DETECT_THRESHOLD = 0.8


@dataclass(frozen=True)
class ImportConfig:
    """What an account's uploads are read with; saved per account after a confirmed import."""

    importer: str  # a built-in importer id, or "csv"
    mapping: CsvMapping | None = None  # required for "csv"

    def to_dict(self) -> dict:
        return {"importer": self.importer, "mapping": self.mapping.to_dict() if self.mapping else None}

    @classmethod
    def from_dict(cls, data: dict) -> "ImportConfig":
        mapping = data.get("mapping")
        return cls(importer=data["importer"], mapping=CsvMapping.from_dict(mapping) if mapping else None)


@dataclass(frozen=True)
class Resolution:
    config: ImportConfig | None  # None: no importer fits and the columns couldn't be guessed
    source: str  # "requested" | "saved" | "detected" | "guessed" | "none"
    suggested_mapping: dict  # guess_mapping() output, to prefill the mapping form


def importer_for(config: ImportConfig) -> Importer:
    if config.importer == CsvMappingImporter.id:
        if config.mapping is None:
            raise ImportFileError("Choose which columns hold the date, description and amount")
        return CsvMappingImporter(config.mapping)
    for importer in BUILTIN_IMPORTERS:
        if importer.id == config.importer:
            return importer
    raise ImportFileError(f"Unknown importer {config.importer!r}")


def resolve(table: Table, requested: ImportConfig | None = None, saved: ImportConfig | None = None) -> Resolution:
    """Pick how to read a file: the user's choice, else the account's saved config
    if it still fits, else a built-in importer that recognizes it, else a guessed mapping."""
    suggestion = guess_mapping(table)
    if requested is not None:
        return Resolution(requested, "requested", suggestion)
    if saved is not None and _fits(saved, table):
        return Resolution(saved, "saved", suggestion)
    scored = [(importer.detect(table), importer) for importer in BUILTIN_IMPORTERS]
    score, best = max(scored, key=lambda s: s[0], default=(0.0, None))
    if best is not None and score >= AUTO_DETECT_THRESHOLD:
        return Resolution(ImportConfig(best.id), "detected", suggestion)
    if all(suggestion[k] for k in ("date_column", "description_column", "amount_column")):
        return Resolution(ImportConfig("csv", CsvMapping.from_dict(suggestion)), "guessed", suggestion)
    return Resolution(None, "none", suggestion)


def _fits(config: ImportConfig, table: Table) -> bool:
    try:
        return importer_for(config).detect(table) > 0
    except ImportFileError:
        return False


__all__ = [
    "AUTO_DETECT_THRESHOLD",
    "BUILTIN_IMPORTERS",
    "AmexSE",
    "CsvMapping",
    "CsvMappingImporter",
    "ImportConfig",
    "Importer",
    "ParsedTransaction",
    "Resolution",
    "Row",
    "Table",
    "guess_mapping",
    "importer_for",
    "parse_amex_csv",
    "read_table",
    "resolve",
]
