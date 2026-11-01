"""What was spent: budgets against spending, monthly summaries, trends and settlements.

What counts as spending depends on the view. For a household it's what's shared
on the accounts shared into it. For a user it's their own share of everything
they can see: their personal spending plus their weighted share of each
household's shared spending, as in the settlement.

A household's settlement says who is responsible for what in a month, and who
pays whom to even out. Closing a month stores it, so later edits don't change it.

A "month" is the period a transaction counts toward (Transaction.period): an
upload is one statement, so 27 Sep – 27 Oct is October.
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
    """Transactions counting toward the months from `start` up to (not including) `end`."""
    return (models.Transaction.period >= start) & (models.Transaction.period < end)


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
            ((t.period, t.category or FALLBACK_CATEGORY), Line(t.amount_minor, t.allocation, t.member_id))
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
            spent[t.period, t.category or FALLBACK_CATEGORY] += t.amount_minor
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


def breakdown(db: Session, scope: Scope, viewer: models.User, month: dt.date) -> schemas.Analysis:
    """Where a month's money went, per category against the month before, and for a household, per member."""
    before = previous_month(month)
    now = _per_category(spent(db, scope, viewer, month, next_month(month)))
    then = _per_category(spent(db, scope, viewer, before, month))
    rows = [
        schemas.AnalysisCategory(category=c, spent_minor=now.get(c, 0), previous_minor=then.get(c, 0))
        for c in set(now) | set(then)
    ]
    rows.sort(key=lambda r: (-r.spent_minor, -r.previous_minor, r.category))
    members = []
    if scope.household_id is not None:
        by_member: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for (_, category), result in _settle_by_month(db, scope.household_id, month, next_month(month)).items():
            for user_id, amount in result.per_member.items():
                if amount:
                    by_member[user_id][category] += amount
        household = db.get(models.Household, scope.household_id)
        members = [
            schemas.AnalysisMember(
                **person(m.user).model_dump(),
                amount_minor=sum(by_member[m.user_id].values()),
                by_category=dict(by_member[m.user_id]),
            )
            for m in household.memberships
        ]
    return schemas.Analysis(
        month=month_label(month),
        spent_minor=sum(now.values()),
        previous_spent_minor=sum(then.values()),
        categories=rows,
        members=members,
    )


def _per_category(spent_by_key: dict[Key, int]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for (_, category), amount in spent_by_key.items():
        totals[category] += amount
    return {c: a for c, a in totals.items() if a}


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
    """Bank-account spending is already paid by the account's owner, so balances become transfers.
    Credit card spending isn't paid by anyone yet, so each card's statement is split into what
    each member pays toward its bill."""
    members = {m.user_id: m for m in hh.memberships}
    weights = _weights(db, hh.id)
    lines: list[Line] = []  # everything, for what each member is responsible for
    paid_lines: list[Line] = []  # bank-account spending: paid already, by the account's owner
    bill_lines: dict[int, list[Line]] = defaultdict(list)  # credit card spending, per card
    cards: dict[int, models.Account] = {}
    unchecked: dict[tuple[int, int | None], int] = defaultdict(int)
    for t in _household_transactions(db, hh.id, month, next_month(month)):
        if not t.reviewed:
            unchecked[t.account_id, t.import_id] += 1
        if t.allocation == Allocation.PERSONAL and t.member_id not in members:
            raise SettlementError(
                f"Transaction {t.id} ({t.description_clean}) is personal for someone who isn't a member"
            )
        if t.account.kind == models.AccountKind.CREDIT:
            line = Line(t.amount_minor, t.allocation, t.member_id)  # nobody has paid it yet
            bill_lines[t.account_id].append(line)
            cards[t.account_id] = t.account
        else:
            # Who paid is whoever owns the account; leaving a household unshares your accounts, so it's a member.
            line = Line(t.amount_minor, t.allocation, t.member_id, payer=t.account.owner_id)
            paid_lines.append(line)
        lines.append(line)

    result = settle(lines, weights)
    balances = settle(paid_lines, weights).balances
    people = {uid: person(m.user) for uid, m in members.items()}
    bills = [_bill(cards[account_id], card_lines, weights, people) for account_id, card_lines in sorted(bill_lines.items())]
    bills = [b for b in bills if b.total_minor]
    on_bills = defaultdict(int)
    for bill in bills:
        for share in bill.shares:
            on_bills[share.user_id] += share.amount_minor
    return schemas.Settlement(
        household_id=hh.id,
        month=month_label(month),
        per_member=[
            schemas.MemberShare(
                **people[uid].model_dump(),
                amount_minor=amount,
                paid_minor=result.paid[uid],
                balance_minor=balances[uid],
                bill_minor=on_bills[uid],
            )
            for uid, amount in result.per_member.items()
        ],
        transfers=[
            schemas.Transfer(debtor=people[t.debtor], creditor=people[t.creditor], amount_minor=t.amount)
            for t in settle_up(balances)
        ],
        bills=bills,
        unchecked=[
            schemas.Unchecked(
                account_id=account_id,
                account_name=db.get(models.Account, account_id).name,
                import_id=import_id,
                period=db.get(models.Import, import_id).period if import_id else None,
                count=count,
            )
            for (account_id, import_id), count in sorted(unchecked.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0))
        ],
        outlay_minor=result.outlay,
        shared_minor=result.shared,
        total_minor=result.total,
    )


def _bill(
    card: models.Account, card_lines: list[Line], weights: dict[int, int], people: dict[int, schemas.Person]
) -> schemas.Bill:
    """What each member pays toward a card's statement; the owner also pays the outlays they fronted."""
    split = settle(card_lines, weights)
    shares = dict(split.per_member)
    shares[card.owner_id] += split.outlay  # the owner is a member: leaving a household unshares their accounts
    return schemas.Bill(
        account_id=card.id,
        account_name=card.name,
        owner=people[card.owner_id],
        total_minor=split.total,
        outlay_minor=split.outlay,
        shares=[schemas.BillShare(**people[uid].model_dump(), amount_minor=amount) for uid, amount in shares.items()],
    )


def statement_review(db: Session, imp: models.Import) -> schemas.StatementReview:
    """How far along going through one statement is, and what it comes to on its own."""
    account = db.get(models.Account, imp.account_id)
    rows = list(db.scalars(select(models.Transaction).where(models.Transaction.import_id == imp.id)))
    if account.household_id is not None:
        weights = _weights(db, account.household_id)
        household = db.get(models.Household, account.household_id)
        people = {m.user_id: person(m.user) for m in household.memberships}
    else:
        weights = {account.owner_id: 1}  # not shared: all of it is the owner's
        people = {account.owner_id: person(account.owner)}
    lines = [
        Line(t.amount_minor, t.allocation, t.member_id)
        for t in rows
        # Personal spending of someone who has left the household isn't anyone's here.
        if t.allocation != Allocation.PERSONAL or t.member_id in weights
    ]
    return schemas.StatementReview(
        statement=schemas.ImportResult.model_validate(imp),
        account_name=account.name,
        account_kind=account.kind,
        total_count=len(rows),
        checked_count=sum(t.reviewed for t in rows),
        split=_bill(account, lines, weights, people),
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
