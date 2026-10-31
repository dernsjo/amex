from collections.abc import Iterable
from datetime import date

from spending_core import ParsedTransaction, categorize, format_minor, to_minor
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def get_users(db: Session) -> list[models.User]:
    return list(db.scalars(select(models.User).where(models.User.active).order_by(models.User.name)))


def get_user_by_name(db: Session, name: str) -> models.User | None:
    return db.scalars(select(models.User).where(models.User.name == name)).first()


def create_or_reactivate_user(db: Session, name: str) -> models.User:
    user = get_user_by_name(db, name)
    if user:
        user.active = True
    else:
        user = models.User(name=name)
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user: models.User) -> None:
    user.active = False
    db.commit()


def has_expenses_paid_by(db: Session, paid_by: str) -> bool:
    return db.scalar(select(exists().where(models.Expense.paid_by == paid_by)))


def paid_by_options(db: Session) -> list[str]:
    return schemas.STANDARD_PAID_BY + [u.name for u in get_users(db)]


def get_expenses(db: Session, skip: int = 0, limit: int | None = None) -> list[models.Expense]:
    query = (
        select(models.Expense)
        .order_by(models.Expense.date.desc(), models.Expense.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(query))


def get_expense(db: Session, expense_id: int) -> models.Expense | None:
    return db.get(models.Expense, expense_id)


def create_expense(db: Session, expense: schemas.ExpenseCreate) -> models.Expense:
    db_expense = models.Expense(
        description=expense.description,
        amount=format_minor(to_minor(expense.amount)),
        date=expense.date or date.today(),
        paid_by=expense.paid_by,
        category=expense.category or categorize(expense.description),
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


def create_expenses_from_import(db: Session, transactions: Iterable[ParsedTransaction]) -> list[models.Expense]:
    db_expenses = [
        models.Expense(
            date=t.booked_on,
            description=t.description,
            amount=format_minor(t.amount_minor),
            paid_by="Split",
            category=categorize(t.description),
        )
        for t in transactions
    ]
    db.add_all(db_expenses)
    db.commit()
    for e in db_expenses:
        db.refresh(e)
    return db_expenses


def update_expenses(db: Session, updates: list[schemas.ExpenseUpdate]) -> list[models.Expense]:
    """Apply all updates in one transaction. Caller has validated ids and values."""
    expenses = []
    for update in updates:
        expense = db.get(models.Expense, update.id)
        if update.paid_by is not None:
            expense.paid_by = update.paid_by
        if update.category is not None:
            expense.category = update.category
        expenses.append(expense)
    db.commit()
    for e in expenses:
        db.refresh(e)
    return expenses


def delete_expense(db: Session, expense: models.Expense) -> None:
    db.delete(expense)
    db.commit()
