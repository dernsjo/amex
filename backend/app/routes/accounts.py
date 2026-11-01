from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import categories, crud, models, schemas
from ..access import Scope, owned_account
from ..auth import get_current_user
from ..database import get_db
from .transactions import validate_category, validate_member

router = APIRouter(prefix="/accounts", tags=["accounts"])


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
    if "household_id" in data.model_fields_set and data.household_id != account.household_id:
        _check_household(db, user, data.household_id)
        account.household_id = data.household_id
        db.flush()
        # Its transactions now follow the new scope's rules.
        only_this = select(models.Account.id).where(models.Account.id == account.id)
        categories.recategorize(db, Scope.of(account), only_this)
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
    category = validate_category(db, account, data.category) if data.category is not None else None
    return crud.create_transaction(db, account, data, category)


def _check_household(db: Session, user: models.User, household_id: int | None) -> None:
    if household_id is not None and not crud.is_member(db, user, household_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Household not found")
