from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import ValidationError
from spending_core import ImportFileError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import imports, models, schemas
from ..access import owned_account, visible_account
from ..categories import month_start
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/accounts/{account_id}/imports", tags=["imports"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
CONFIG_HELP = "Optional JSON ImportConfig; without it the account's saved config, or auto-detection, is used"


@router.post("/preview", response_model=schemas.ImportPreview)
async def preview_import(
    file: UploadFile = File(...),
    config: str | None = Form(None, description=CONFIG_HELP),
    account: models.Account = Depends(owned_account),
    db: Session = Depends(get_db),
):
    """Read a file without storing anything: how it was understood, the rows, and which are duplicates."""
    return (await _prepare(db, account, file, config)).preview


@router.post("", response_model=schemas.ImportResult, status_code=status.HTTP_201_CREATED)
async def confirm_import(
    file: UploadFile = File(...),
    config: str | None = Form(None, description=CONFIG_HELP),
    account: models.Account = Depends(owned_account),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import the file's new rows and save the config, so the account's next upload is read the same way."""
    prepared = await _prepare(db, account, file, config)
    try:
        return imports.confirm(db, account, user, prepared)
    except ImportFileError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None


@router.get("", response_model=list[schemas.ImportResult])
def list_imports(account: models.Account = Depends(visible_account), db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(models.Import)
            .where(models.Import.account_id == account.id)
            .order_by(models.Import.created_at.desc(), models.Import.id.desc())
        )
    )


@router.patch("/{import_id}", response_model=schemas.ImportResult)
def update_import(
    import_id: int,
    data: schemas.ImportUpdate,
    account: models.Account = Depends(owned_account),
    db: Session = Depends(get_db),
):
    """Move an upload to another month; months already closed keep what they stored."""
    imp = _own_import(db, account, import_id)
    imports.set_period(db, imp, month_start(data.period))
    return imp


@router.delete("/{import_id}", status_code=status.HTTP_204_NO_CONTENT)
def undo_import(
    import_id: int,
    account: models.Account = Depends(owned_account),
    db: Session = Depends(get_db),
):
    """Delete an import together with its transactions."""
    imp = _own_import(db, account, import_id)
    db.delete(imp)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _own_import(db: Session, account: models.Account, import_id: int) -> models.Import:
    imp = db.get(models.Import, import_id)
    if imp is None or imp.account_id != account.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import not found")
    return imp


async def _prepare(db: Session, account: models.Account, file: UploadFile, config: str | None) -> imports.Prepared:
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is larger than 5 MB")
    try:
        requested = schemas.ImportConfig.model_validate_json(config) if config else None
    except ValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid config: {e.errors()}") from None
    try:
        return imports.prepare(db, account, file.filename or "upload.csv", contents, requested)
    except ImportFileError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
