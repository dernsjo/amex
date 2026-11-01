from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from spending_core import Allocation
from sqlalchemy.orm import Session

from .. import categories, crud, models, schemas
from ..access import Scope, membership, visible_account, visible_transactions
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=list[schemas.Transaction])
def list_transactions(
    account_id: int | None = None,
    household_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Everything you can see, or only one account / the accounts shared into one household."""
    if account_id is not None:
        visible_account(account_id, user, db)
    if household_id is not None:
        membership(household_id, user, db)
    return crud.get_transactions(db, user, account_id, household_id, skip, limit)


@router.patch("/transactions", response_model=list[schemas.Transaction])
def update_transactions(
    updates: list[schemas.TransactionUpdate],
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change allocation, member and/or category of one or more transactions, all or nothing.

    Anyone who can see a transaction can change these, so household members can
    mark exceptions on each other's shared accounts.
    """
    found = visible_transactions(db, user, [u.id for u in updates])
    missing = [u.id for u in updates if u.id not in found]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Transaction(s) not found: {missing}")

    for update in updates:
        t = found[update.id]
        if update.category is not None:
            t.category = validate_category(db, t.account, update.category)
            t.category_manual = True
        if update.allocation is not None:
            t.allocation = update.allocation
        elif update.member_id is not None:
            t.allocation = Allocation.PERSONAL
        if t.allocation == Allocation.PERSONAL:
            t.member_id = update.member_id or t.member_id or t.account.owner_id
            validate_member(t.account, t.member_id)
        else:
            t.member_id = None
    db.commit()
    return [found[u.id] for u in updates]


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = visible_transactions(db, user, [transaction_id]).get(transaction_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    if t.account.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the account owner can delete transactions")
    db.delete(t)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def validate_member(account: models.Account, member_id: int) -> None:
    allowed = crud.assignable_people(account)
    if member_id not in {u.id for u in allowed}:
        names = ", ".join(f"{u.display_name} ({u.id})" for u in allowed)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"member_id must be one of: {names}")


def validate_category(db: Session, account: models.Account, category: str) -> str:
    """The category's name as the account's scope spells it."""
    found = categories.find_category(db, Scope.of(account), category)
    if found is None:
        names = categories.category_names(db, Scope.of(account))
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid category {category!r}; expected one of {names}"
        )
    return found.name
