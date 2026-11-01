"""Upload → preview → confirm.

Both steps receive the file; nothing is stored between them, and the raw file
is never kept (only its hash, to recognize a re-upload).
"""

import hashlib
from dataclasses import dataclass

from spending_core import (
    BUILTIN_IMPORTERS,
    CsvMapping,
    ImportConfig,
    ImportFileError,
    ParsedTransaction,
    dedupe_hashes,
    importer_for,
    read_table,
    resolve,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import categories, crud, models, schemas
from .access import Scope

PREVIEW_SAMPLE_ROWS = 5
IMPORTERS = [schemas.ImporterInfo(id=i.id, name=i.name) for i in BUILTIN_IMPORTERS] + [
    schemas.ImporterInfo(id="csv", name="CSV with column mapping")
]


@dataclass
class Prepared:
    """A file read against an account, before anything is stored."""

    preview: schemas.ImportPreview
    config: ImportConfig | None
    parsed: list[ParsedTransaction]
    hashes: list[str]
    duplicates: set[str]
    file_hash: str


def to_core_config(config: schemas.ImportConfig) -> ImportConfig:
    mapping = CsvMapping(**config.mapping.model_dump()) if config.mapping else None
    return ImportConfig(config.importer, mapping)


def prepare(
    db: Session,
    acc: models.Account,
    filename: str,
    content: bytes,
    requested: schemas.ImportConfig | None,
) -> Prepared:
    """Read the file and mark duplicates. Raises ImportFileError only if the file isn't a table at all;
    a config that doesn't fit is reported in `preview.error` so the user can fix it."""
    table = read_table(content)
    saved = ImportConfig.from_dict(acc.import_config) if acc.import_config else None
    resolution = resolve(table, to_core_config(requested) if requested else None, saved)
    config = resolution.config
    file_hash = hashlib.sha256(content).hexdigest()

    parsed: list[ParsedTransaction] = []
    error = None
    if config is None:
        error = "Couldn't tell which columns hold the date, description and amount; choose them below"
    else:
        try:
            parsed = importer_for(config).parse(table)
        except ImportFileError as e:
            error = str(e)

    hashes = dedupe_hashes(acc.id, parsed)
    categorize = categories.categorizer(db, Scope.of(acc))
    duplicates = set(
        db.scalars(
            select(models.Transaction.dedupe_hash).where(
                models.Transaction.account_id == acc.id, models.Transaction.dedupe_hash.in_(hashes)
            )
        )
    )
    previous = db.scalars(
        select(models.Import.created_at)
        .where(models.Import.account_id == acc.id, models.Import.file_hash == file_hash)
        .order_by(models.Import.created_at.desc())
    ).first()

    rows = [
        schemas.PreviewTransaction(
            booked_on=t.booked_on,
            description=t.description,
            amount_minor=t.amount_minor,
            category=categorize(t.description),
            duplicate=h in duplicates,
        )
        for t, h in zip(parsed, hashes, strict=True)
    ]
    duplicate_count = sum(r.duplicate for r in rows)
    preview = schemas.ImportPreview(
        filename=filename,
        config=schemas.ImportConfig.model_validate(config.to_dict()) if config else None,
        source=resolution.source,
        importers=IMPORTERS,
        suggested_mapping=schemas.SuggestedMapping(**resolution.suggested_mapping),
        columns=table.header,
        sample_rows=[r.cells for r in table.rows[:PREVIEW_SAMPLE_ROWS]],
        transactions=rows,
        new_count=len(rows) - duplicate_count,
        duplicate_count=duplicate_count,
        already_imported_at=previous,
        error=error,
    )
    return Prepared(preview, config, parsed, hashes, duplicates, file_hash)


def confirm(db: Session, acc: models.Account, user: models.User, prepared: Prepared) -> models.Import:
    """Store the new rows and remember the config for the account's next upload."""
    if prepared.config is None or prepared.preview.error:
        raise ImportFileError(prepared.preview.error or "Nothing to import")
    parsed = prepared.parsed
    imp = models.Import(
        account_id=acc.id,
        created_by_id=user.id,
        importer=prepared.config.importer,
        filename=prepared.preview.filename,
        file_hash=prepared.file_hash,
        period_start=min((t.booked_on for t in parsed), default=None),
        period_end=max((t.booked_on for t in parsed), default=None),
    )
    db.add(imp)
    db.flush()

    new = _new_transactions(acc, imp, prepared)
    db.add_all(new)
    imp.transaction_count = len(new)
    imp.duplicate_count = len(parsed) - len(new)
    acc.import_config = prepared.config.to_dict()
    db.commit()
    db.refresh(imp)
    return imp


def _new_transactions(acc: models.Account, imp: models.Import, prepared: Prepared) -> list[models.Transaction]:
    allocation, member_id = crud.default_allocation(acc)
    return [
        models.Transaction(
            account_id=acc.id,
            import_id=imp.id,
            booked_on=t.booked_on,
            description_raw=t.description,
            description_clean=t.description,
            amount_minor=t.amount_minor,
            currency=acc.currency,
            allocation=allocation,
            member_id=member_id,
            category=row.category,  # as previewed
            dedupe_hash=h,
        )
        for t, row, h in zip(prepared.parsed, prepared.preview.transactions, prepared.hashes, strict=True)
        if h not in prepared.duplicates
    ]
