import hashlib
from collections.abc import Sequence
from datetime import date

from spending_core import (
    Allocation,
    Line,
    ParsedTransaction,
    categorize,
    dedupe_hashes,
    settle,
    to_minor,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, schemas
from .access import household_ids_of, visible_account_ids


def person(user: models.User) -> schemas.Person:
    return schemas.Person(user_id=user.id, display_name=user.display_name)


# Users and households

def me(db: Session, user: models.User) -> schemas.Me:
    memberships = db.scalars(
        select(models.Membership).where(models.Membership.user_id == user.id).order_by(models.Membership.id)
    )
    return schemas.Me(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        households=[schemas.HouseholdSummary(id=m.household_id, name=m.household.name, role=m.role) for m in memberships],
    )


def get_user_by_email(db: Session, email: str) -> models.User | None:
    # Exact, case-insensitive match (not ilike, where '_' and '%' are wildcards).
    return db.scalars(select(models.User).where(func.lower(models.User.email) == email.strip().lower())).first()


def household(household: models.Household) -> schemas.Household:
    return schemas.Household(
        id=household.id,
        name=household.name,
        members=[
            schemas.Member(
                user_id=m.user_id,
                display_name=m.user.display_name,
                email=m.user.email,
                role=m.role,
                split_weight=m.split_weight,
            )
            for m in household.memberships
        ],
    )


def create_household(db: Session, user: models.User, name: str) -> models.Household:
    hh = models.Household(name=name)
    hh.memberships.append(models.Membership(user=user, role=models.Role.OWNER))
    db.add(hh)
    db.commit()
    db.refresh(hh)
    return hh


def remove_member(db: Session, member: models.Membership) -> None:
    """Remove a member; their accounts stop being shared, and an empty household is deleted."""
    hh = member.household
    for account in db.scalars(
        select(models.Account).where(
            models.Account.household_id == hh.id, models.Account.owner_id == member.user_id
        )
    ):
        account.household_id = None
    hh.memberships.remove(member)
    if not hh.memberships:
        db.delete(hh)
    db.commit()


# Accounts

def visible_accounts(db: Session, user: models.User) -> list[models.Account]:
    return list(
        db.scalars(select(models.Account).where(models.Account.id.in_(visible_account_ids(user))).order_by(models.Account.id))
    )


def assignable_people(account: models.Account) -> list[models.User]:
    """The owner, plus the household's members when the account is shared."""
    if account.household is None:
        return [account.owner]
    return [m.user for m in account.household.memberships]


def account(acc: models.Account) -> schemas.Account:
    return schemas.Account(
        id=acc.id,
        name=acc.name,
        currency=acc.currency,
        owner=person(acc.owner),
        household_id=acc.household_id,
        members=[person(u) for u in assignable_people(acc)],
    )


def is_member(db: Session, user: models.User, household_id: int) -> bool:
    return db.scalar(select(household_ids_of(user).where(models.Membership.household_id == household_id).exists()))


# Transactions

def get_transactions(
    db: Session,
    user: models.User,
    account_id: int | None = None,
    household_id: int | None = None,
    skip: int = 0,
    limit: int | None = None,
) -> list[models.Transaction]:
    query = select(models.Transaction).where(models.Transaction.account_id.in_(visible_account_ids(user)))
    if account_id is not None:
        query = query.where(models.Transaction.account_id == account_id)
    if household_id is not None:
        shared = select(models.Account.id).where(models.Account.household_id == household_id)
        query = query.where(models.Transaction.account_id.in_(shared))
    query = query.order_by(models.Transaction.booked_on.desc(), models.Transaction.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(query))


def default_allocation(acc: models.Account) -> tuple[Allocation, int | None]:
    """Spending on a shared account is shared until someone says otherwise; otherwise it's the owner's."""
    if acc.household_id is not None:
        return Allocation.SHARED, None
    return Allocation.PERSONAL, acc.owner_id


def create_transaction(db: Session, acc: models.Account, data: schemas.TransactionCreate) -> models.Transaction:
    allocation, member_id = default_allocation(acc)
    if data.allocation is not None:
        allocation, member_id = data.allocation, data.member_id
    elif data.member_id is not None:
        allocation, member_id = Allocation.PERSONAL, data.member_id
    if allocation == Allocation.PERSONAL and member_id is None:
        member_id = acc.owner_id
    description = " ".join(data.description.split())
    t = models.Transaction(
        account_id=acc.id,
        booked_on=data.booked_on or date.today(),
        description_raw=data.description,
        description_clean=description,
        amount_minor=to_minor(data.amount),
        currency=acc.currency,
        allocation=allocation,
        member_id=member_id if allocation == Allocation.PERSONAL else None,
        category=data.category or categorize(description),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def import_transactions(
    db: Session,
    acc: models.Account,
    user: models.User,
    importer: str,
    filename: str,
    content: bytes,
    parsed: Sequence[ParsedTransaction],
) -> models.Import:
    """Store parsed rows, skipping ones already imported into this account."""
    hashes = dedupe_hashes(acc.id, parsed)
    existing = set(
        db.scalars(
            select(models.Transaction.dedupe_hash).where(
                models.Transaction.account_id == acc.id, models.Transaction.dedupe_hash.in_(hashes)
            )
        )
    )
    imp = models.Import(
        account_id=acc.id,
        created_by_id=user.id,
        importer=importer,
        filename=filename,
        file_hash=hashlib.sha256(content).hexdigest(),
        period_start=min((t.booked_on for t in parsed), default=None),
        period_end=max((t.booked_on for t in parsed), default=None),
    )
    db.add(imp)
    db.flush()

    allocation, member_id = default_allocation(acc)
    new = []
    for t, h in zip(parsed, hashes, strict=True):
        if h in existing:
            continue
        new.append(
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
                category=categorize(t.description),
                dedupe_hash=h,
            )
        )
    db.add_all(new)
    imp.transaction_count = len(new)
    imp.duplicate_count = len(parsed) - len(new)
    db.commit()
    db.refresh(imp)
    return imp


# Settlement

class SettlementError(ValueError):
    pass


def settlement(db: Session, hh: models.Household) -> schemas.Settlement:
    """Who is responsible for what across the accounts shared into the household."""
    members = {m.user_id: m for m in hh.memberships}
    lines = []
    for t in get_household_transactions(db, hh.id):
        if t.allocation == Allocation.PERSONAL and t.member_id not in members:
            raise SettlementError(
                f"Transaction {t.id} ({t.description_clean}) is personal for someone who isn't a member"
            )
        lines.append(Line(t.amount_minor, t.allocation, t.member_id))

    # Without any weight the split is undefined; fall back to an even split.
    weights = {uid: m.split_weight for uid, m in members.items()}
    if sum(weights.values()) == 0:
        weights = dict.fromkeys(members, 1)
    result = settle(lines, weights)
    return schemas.Settlement(
        household_id=hh.id,
        per_member=[
            schemas.MemberShare(user_id=uid, display_name=members[uid].user.display_name, amount_minor=amount)
            for uid, amount in result.per_member.items()
        ],
        outlay_minor=result.outlay,
        shared_minor=result.shared,
        total_minor=result.total,
    )


def get_household_transactions(db: Session, household_id: int) -> list[models.Transaction]:
    shared = select(models.Account.id).where(models.Account.household_id == household_id)
    return list(db.scalars(select(models.Transaction).where(models.Transaction.account_id.in_(shared))))
