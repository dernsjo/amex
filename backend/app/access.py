"""The one place that decides what a user may see.

Every route that touches accounts, transactions or households goes through these
dependencies; anything not visible answers 404 so ids don't leak existence.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import ColumnElement, Select, or_, select
from sqlalchemy.orm import Session

from . import models
from .auth import get_current_user
from .database import get_db


def household_ids_of(user: models.User) -> Select:
    return select(models.Membership.household_id).where(models.Membership.user_id == user.id)


def visible_account_ids(user: models.User) -> Select:
    """Accounts the user owns, plus accounts shared into their households."""
    return select(models.Account.id).where(
        or_(models.Account.owner_id == user.id, models.Account.household_id.in_(household_ids_of(user)))
    )


def _not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


def visible_account(
    account_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.Account:
    account = db.scalars(
        select(models.Account).where(models.Account.id == account_id, models.Account.id.in_(visible_account_ids(user)))
    ).first()
    if account is None:
        raise _not_found("Account")
    return account


def owned_account(
    account: models.Account = Depends(visible_account),
    user: models.User = Depends(get_current_user),
) -> models.Account:
    """Changing an account, importing into it or deleting from it is for its owner only."""
    if account.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the account owner can do this")
    return account


def membership(
    household_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.Membership:
    member = db.scalars(
        select(models.Membership).where(
            models.Membership.household_id == household_id, models.Membership.user_id == user.id
        )
    ).first()
    if member is None:
        raise _not_found("Household")
    return member


def owner_membership(member: models.Membership = Depends(membership)) -> models.Membership:
    if member.role != models.Role.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a household owner can do this")
    return member


def visible_transactions(db: Session, user: models.User, ids: list[int]) -> dict[int, models.Transaction]:
    rows = db.scalars(
        select(models.Transaction).where(
            models.Transaction.id.in_(ids), models.Transaction.account_id.in_(visible_account_ids(user))
        )
    )
    return {t.id: t for t in rows}


@dataclass(frozen=True)
class Scope:
    user_id: int | None = None
    household_id: int | None = None

    @staticmethod
    def of(account: models.Account) -> "Scope":
        if account.household_id is not None:
            return Scope(household_id=account.household_id)
        return Scope(user_id=account.owner_id)

    def owns(self, model: type[models.Scoped]) -> ColumnElement[bool]:
        if self.household_id is not None:
            return model.household_id == self.household_id
        return model.user_id == self.user_id

    def fields(self) -> dict[str, int | None]:
        return {"user_id": self.user_id, "household_id": self.household_id}

    def account_ids(self) -> Select:
        """The accounts categorized with this scope."""
        if self.household_id is not None:
            return select(models.Account.id).where(models.Account.household_id == self.household_id)
        return select(models.Account.id).where(
            models.Account.owner_id == self.user_id, models.Account.household_id.is_(None)
        )


def scope(
    household_id: int | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scope:
    """Categories and budgets of a household you're in (`?household_id=`), or else your own."""
    if household_id is None:
        return Scope(user_id=user.id)
    membership(household_id, user, db)
    return Scope(household_id=household_id)
