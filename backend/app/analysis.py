"""What was spent: budgets against spending, monthly summaries, trends and settlements.

What counts as spending depends on the view. For a household it's what's shared
on the accounts shared into it. For a user it's their own share of everything
they can see: their personal spending plus their weighted share of each
household's shared spending, as in the settlement.

A household's settlement says who is responsible for what in a month, and who
pays whom to even out. Closing a month stores it, so later edits don't change it.
"""

import datetime as dt
from collections import defaultdict
from collections.abc import Iterable

from spending_core import FALLBACK_CATEGORY, Allocation, Line, settle, settle_by_category, settle_up
from spending_core import Settlement as Result
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from . import categories, models, schemas
from .access import Scope, household_ids_of, visible_account_ids
from .categories import next_month
from .crud import person

LARGEST = 10  # transactions in a summary
MAX_TREND_MONTHS = 36

# (first day of the month, category name)
Key = tuple[dt.date, str]


def month_label(month: dt.date) -> str:
    return month.strftime("%Y-%m")


def months(first: dt.date, last: dt.date) -> list[dt.date]:
    result = [first]
    while result[-1] < last:
        result.append(next_month(result[-1]))
    return result


def previous_month(month: dt.date) -> dt.date:
    return (month - dt.timedelta(days=1)).replace(day=1)


def _between(start: dt.date, end: dt.date) -> ColumnElement[bool]:
    return (models.Transaction.booked_on >= start) & (models.Transaction.booked_on < end)


# Spending


def _weights(db: Session, household_id: int) -> dict[int, int]:
    weights = {
        m.user_id: m.split_weight
        for m in db.scalars(
            select(models.Membership).where(models.Membership.household_id == household_id).order_by(models.Membership.id)
        )
    }
    # Without any weight the split is undefined; fall back to an even split.
    if sum(weights.values()) == 0:
        weights = dict.fromkeys(weights, 1)
    return weights


def _household_transactions(db: Session, household_id: int, start: dt.date, end: dt.date) -> Iterable[models.Transaction]:
    return db.scalars(
        select(models.Transaction)
        .where(models.Transaction.account_id.in_(Scope(household_id=household_id).account_ids()), _between(start, end))
        .order_by(models.Transaction.id)
    )


def _settle_by_month(db: Session, household_id: int, start: dt.date, end: dt.date) -> dict[Key, Result]:
    weights = _weights(db, household_id)
    return settle_by_category(
        [
            ((t.booked_on.replace(day=1), t.category or FALLBACK_CATEGORY), Line(t.amount_minor, t.allocation, t.member_id))
            for t in _household_transactions(db, household_id, start, end)
            # Personal spending of someone who has left the household isn't anyone's here.
            if t.allocation != Allocation.PERSONAL or t.member_id in weights
        ],
        weights,
    )


def _own_share(db: Session, user: models.User, start: dt.date, end: dt.date) -> dict[Key, int]:
    spent: dict[Key, int] = defaultdict(int)
    for t in db.scalars(
        select(models.Transaction).where(
            models.Transaction.account_id.in_(Scope(user_id=user.id).account_ids()), _between(start, end)
        )
    ):
        if t.allocation == Allocation.SHARED or (t.allocation == Allocation.PERSONAL and t.member_id == user.id):
            spent[t.booked_on.replace(day=1), t.category or FALLBACK_CATEGORY] += t.amount_minor
    for household_id in db.scalars(household_ids_of(user)):
        for key, result in _settle_by_month(db, household_id, start, end).items():
            spent[key] += result.per_member.get(user.id, 0)
    return dict(spent)


def spent(db: Session, scope: Scope, viewer: models.User, start: dt.date, end: dt.date) -> dict[Key, int]:
    """Spending per month and category from `start` up to (not including) `end`."""
    if scope.household_id is not None:
        return {key: result.shared for key, result in _settle_by_month(db, scope.household_id, start, end).items()}
    return _own_share(db, viewer, start, end)


def counted_transactions(db: Session, scope: Scope, viewer: models.User):
    """The transactions that count toward a view's spending, as a query to narrow down."""
    query = select(models.Transaction)
    if scope.household_id is not None:
        return query.where(
            models.Transaction.account_id.in_(scope.account_ids()), models.Transaction.allocation == Allocation.SHARED
        )
    return query.where(
        models.Transaction.account_id.in_(visible_account_ids(viewer)),
        (models.Transaction.allocation == Allocation.SHARED)
        | ((models.Transaction.allocation == Allocation.PERSONAL) & (models.Transaction.member_id == viewer.id)),
    )


# Budgets, summary and trends


def budget_month(db: Session, scope: Scope, viewer: models.User, month: dt.date) -> schemas.BudgetMonth:
    """Each category's target against what was spent in one month."""
    names = categories.category_names(db, scope)
    recurring: dict[str, int] = {}
    override: dict[str, int] = {}
    for b in db.scalars(
        select(models.Budget).where(
            scope.owns(models.Budget), models.Budget.month.is_(None) | (models.Budget.month == month)
        )
    ):
        (recurring if b.month is None else override)[b.category] = b.amount_minor

    by_category = {category: amount for (_, category), amount in spent(db, scope, viewer, month, next_month(month)).items()}
    lines = [
        schemas.BudgetLine(
            category=name,
            recurring_minor=recurring.get(name),
            override_minor=override.get(name),
            target_minor=override.get(name, recurring.get(name)),
            spent_minor=by_category.get(name, 0),
        )
        for name in [*names, *sorted((set(by_category) | set(recurring) | set(override)) - set(names))]
    ]
    return schemas.BudgetMonth(
        month=month_label(month),
        lines=lines,
        target_minor=sum(line.target_minor or 0 for line in lines),
        spent_minor=sum(line.spent_minor for line in lines),
    )


def summary(db: Session, scope: Scope, viewer: models.User, month: dt.date) -> schemas.Summary:
    budget = budget_month(db, scope, viewer, month)
    largest = db.scalars(
        counted_transactions(db, scope, viewer)
        .where(_between(month, next_month(month)))
        .order_by(models.Transaction.amount_minor.desc(), models.Transaction.id)
        .limit(LARGEST)
    )
    before = previous_month(month)
    return schemas.Summary(
        **budget.model_dump(),
        largest=[schemas.Transaction.model_validate(t) for t in largest],
        previous_spent_minor=sum(spent(db, scope, viewer, before, month).values()),
    )


def trends(db: Session, scope: Scope, viewer: models.User, first: dt.date, last: dt.date) -> schemas.Trends:
    """Spending per month and category, for every month from `first` through `last`."""
    per_month: dict[dt.date, dict[str, int]] = {m: {} for m in months(first, last)}
    for (month, category), amount in sorted(spent(db, scope, viewer, first, next_month(last)).items()):
        if amount:
            per_month[month][category] = amount
    return schemas.Trends(
        months=[
            schemas.TrendMonth(month=month_label(m), spent_minor=sum(by.values()), by_category=by)
            for m, by in per_month.items()
        ]
    )


# Settlement


class SettlementError(ValueError):
    pass


def settlement(db: Session, hh: models.Household, month: dt.date) -> schemas.Settlement:
    """The month's settlement: stored if the month is closed, else worked out from the transactions now."""
    closed = closed_month(db, hh.id, month)
    if closed is not None:
        return _stored(closed)
    return _calculate(db, hh, month)


def _calculate(db: Session, hh: models.Household, month: dt.date) -> schemas.Settlement:
    members = {m.user_id: m for m in hh.memberships}
    lines = []
    for t in _household_transactions(db, hh.id, month, next_month(month)):
        if t.allocation == Allocation.PERSONAL and t.member_id not in members:
            raise SettlementError(
                f"Transaction {t.id} ({t.description_clean}) is personal for someone who isn't a member"
            )
        # Who paid is whoever owns the account; leaving a household unshares your accounts, so it's a member.
        lines.append(Line(t.amount_minor, t.allocation, t.member_id, payer=t.account.owner_id))

    result = settle(lines, _weights(db, hh.id))
    people = {uid: person(m.user) for uid, m in members.items()}
    balances = result.balances
    return schemas.Settlement(
        household_id=hh.id,
        month=month_label(month),
        per_member=[
            schemas.MemberShare(
                **people[uid].model_dump(),
                amount_minor=amount,
                paid_minor=result.paid[uid],
                balance_minor=balances[uid],
            )
            for uid, amount in result.per_member.items()
        ],
        transfers=[
            schemas.Transfer(debtor=people[t.debtor], creditor=people[t.creditor], amount_minor=t.amount)
            for t in settle_up(balances)
        ],
        outlay_minor=result.outlay,
        shared_minor=result.shared,
        total_minor=result.total,
    )


def _stored(closed: models.Settlement) -> schemas.Settlement:
    return schemas.Settlement.model_validate({**closed.result, "closed_at": closed.closed_at})


def closed_month(db: Session, household_id: int, month: dt.date) -> models.Settlement | None:
    return db.scalars(
        select(models.Settlement).where(models.Settlement.household_id == household_id, models.Settlement.month == month)
    ).first()


def closed_months(db: Session, household_id: int) -> list[schemas.Settlement]:
    rows = db.scalars(
        select(models.Settlement)
        .where(models.Settlement.household_id == household_id)
        .order_by(models.Settlement.month.desc())
    )
    return [_stored(row) for row in rows]


def close_month(db: Session, hh: models.Household, user: models.User, month: dt.date) -> schemas.Settlement:
    result = _calculate(db, hh, month)
    row = models.Settlement(
        household_id=hh.id,
        month=month,
        result=result.model_dump(mode="json", exclude={"closed_at"}),
        closed_by_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _stored(row)
