from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from spending_core import ImportFileError, parse_amex_csv
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..access import owned_account
from ..auth import get_current_user
from ..database import get_db
from .transactions import validate_category, validate_member

router = APIRouter(prefix="/accounts", tags=["accounts"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.get("", response_model=list[schemas.Account])
def list_accounts(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Accounts you own and accounts shared into your households."""
    return [crud.account(a) for a in crud.visible_accounts(db, user)]


@router.post("", response_model=schemas.Account, status_code=status.HTTP_201_CREATED)
def create_account(
    data: schemas.AccountCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_household(db, user, data.household_id)
    account = models.Account(
        owner=user, name=data.name.strip(), currency=data.currency.upper(), household_id=data.household_id
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return crud.account(account)


@router.patch("/{account_id}", response_model=schemas.Account)
def update_account(
    data: schemas.AccountUpdate,
    account: models.Account = Depends(owned_account),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.name is not None:
        account.name = data.name.strip()
    if "household_id" in data.model_fields_set:
        _check_household(db, user, data.household_id)
        account.household_id = data.household_id
    db.commit()
    db.refresh(account)
    return crud.account(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account: models.Account = Depends(owned_account), db: Session = Depends(get_db)):
    """Deletes the account with all its imports and transactions."""
    db.delete(account)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{account_id}/transactions", response_model=schemas.Transaction, status_code=status.HTTP_201_CREATED
)
def create_transaction(
    data: schemas.TransactionCreate,
    account: models.Account = Depends(owned_account),
    db: Session = Depends(get_db),
):
    if data.member_id is not None:
        validate_member(account, data.member_id)
    if data.category is not None:
        validate_category(data.category)
    return crud.create_transaction(db, account, data)


@router.post("/{account_id}/imports", response_model=schemas.ImportResult, status_code=status.HTTP_201_CREATED)
async def upload_import(
    file: UploadFile = File(...),
    account: models.Account = Depends(owned_account),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import an Amex CSV export. Rows already imported into this account are skipped."""
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is larger than 5 MB")
    try:
        parsed = parse_amex_csv(contents)
    except ImportFileError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
    return crud.import_transactions(db, account, user, "amex_se", file.filename or "upload.csv", contents, parsed)


def _check_household(db: Session, user: models.User, household_id: int | None) -> None:
    if household_id is not None and not crud.is_member(db, user, household_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Household not found")
