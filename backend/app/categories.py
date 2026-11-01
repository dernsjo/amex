"""Categories, category rules and budgets, per scope.

A scope is a user (their unshared accounts) or a household (the accounts shared
into it). An account's transactions are categorized with its scope's rules, so
sharing an account into a household switches it to the household's categories.
A scope gets a copy of the default categories the first time it's used.
"""

import datetime as dt

from spending_core import DEFAULT_CATEGORIES, FALLBACK_CATEGORY, Categorizer, Rule
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from . import models
from .access import Scope


# Categories


def categories(db: Session, scope: Scope) -> list[models.Category]:
    """The scope's categories, seeding the defaults on first use."""
    rows = list(db.scalars(select(models.Category).where(scope.owns(models.Category)).order_by(models.Category.id)))
    if not rows:
        rows = [models.Category(name=name, default_key=name, **scope.fields()) for name in DEFAULT_CATEGORIES]
        db.add_all(rows)
        db.flush()
    return rows


def category_names(db: Session, scope: Scope) -> list[str]:
    return [c.name for c in categories(db, scope)]


def find_category(db: Session, scope: Scope, name: str) -> models.Category | None:
    key = name.strip().casefold()
    return next((c for c in categories(db, scope) if c.name.casefold() == key), None)


def is_fallback(category: models.Category) -> bool:
    return category.default_key == FALLBACK_CATEGORY


def categorizer(db: Session, scope: Scope) -> Categorizer:
    rules = db.scalars(
        select(models.CategoryRule).where(scope.owns(models.CategoryRule)).order_by(models.CategoryRule.id.desc())
    )
    names = {c.default_key: c.name for c in categories(db, scope) if c.default_key}
    return Categorizer([Rule(r.pattern, r.category) for r in rules], names)


def recategorize(db: Session, scope: Scope, account_ids: Select | None = None) -> int:
    """Re-run the rules on transactions nobody categorized by hand. Returns how many changed."""
    categorize = categorizer(db, scope)
    changed = 0
    for t in db.scalars(
        select(models.Transaction).where(
            models.Transaction.account_id.in_(account_ids if account_ids is not None else scope.account_ids()),
            models.Transaction.category_manual.is_(False),
        )
    ):
        category = categorize(t.description_clean)
        if t.category != category:
            t.category = category
            changed += 1
    return changed


def rename(db: Session, scope: Scope, category: models.Category, name: str) -> None:
    """Rename everywhere in the scope: rules, budgets and transactions follow."""
    old = category.name
    category.name = name
    for model in (models.CategoryRule, models.Budget):
        for row in db.scalars(select(model).where(scope.owns(model), model.category == old)):
            row.category = name
    for t in db.scalars(
        select(models.Transaction).where(
            models.Transaction.account_id.in_(scope.account_ids()), models.Transaction.category == old
        )
    ):
        t.category = name


def delete(db: Session, scope: Scope, category: models.Category) -> None:
    """Delete with its rules and budgets; its transactions are categorized again without it."""
    name = category.name
    for model in (models.CategoryRule, models.Budget):
        for row in db.scalars(select(model).where(scope.owns(model), model.category == name)):
            db.delete(row)
    db.delete(category)
    db.flush()
    for t in db.scalars(
        select(models.Transaction).where(
            models.Transaction.account_id.in_(scope.account_ids()), models.Transaction.category == name
        )
    ):
        t.category_manual = False
    recategorize(db, scope)


# Budgets


def month_start(month: str) -> dt.date:
    return dt.date.fromisoformat(f"{month}-01")


def next_month(day: dt.date) -> dt.date:
    return (day.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def set_budget(db: Session, scope: Scope, category: str, month: dt.date | None, amount_minor: int | None) -> None:
    """Set (or with amount None, remove) the target for every month, or only for `month`."""
    budget = db.scalars(
        select(models.Budget).where(
            scope.owns(models.Budget),
            models.Budget.category == category,
            models.Budget.month.is_(None) if month is None else models.Budget.month == month,
        )
    ).first()
    if amount_minor is None:
        if budget is not None:
            db.delete(budget)
    elif budget is None:
        db.add(models.Budget(category=category, month=month, amount_minor=amount_minor, **scope.fields()))
    else:
        budget.amount_minor = amount_minor
