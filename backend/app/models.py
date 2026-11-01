"""Database tables.

Data belongs to users: a user owns accounts, and transactions belong to an
account. A household is optional; an owner can share an account into one, which
lets the other members see and allocate its transactions. Access is therefore
always "accounts I own, or accounts shared into a household I'm a member of"
(see access.py).

Categories, category rules and budgets belong to a scope: a user (for their
unshared accounts) or a household (for the accounts shared into it). Transactions
store the category by name, so "Groceries" adds up across scopes in "My view".

A household can close a month, which stores its settlement as a snapshot.
"Month" means the period a transaction counts toward (Transaction.period): an
upload is one statement and counts toward one month, so a card statement for
27 Sep – 27 Oct is October. Transactions added by hand count toward their own month.
"""

import datetime as dt
from enum import StrEnum

from spending_core import Allocation
from sqlalchemy import JSON, BigInteger, CheckConstraint, Enum, ForeignKey, Index, String, UniqueConstraint, false, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class AccountKind(StrEnum):
    """How an account's spending is paid: a bank account's is paid as it happens, by
    its owner; a credit card's is paid later, as one bill per statement."""

    DEBIT = "debit"
    CREDIT = "credit"


def _enum(enum_class: type[StrEnum]) -> Enum:
    # Stored as plain strings (no Postgres ENUM type), so adding a value needs no migration.
    return Enum(enum_class, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Supabase user id (JWT `sub`). Null for someone added to a household before
    # signing in; they take over this row on first sign-in with the same email.
    auth_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="household", cascade="all, delete-orphan", order_by="Membership.id"
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("household_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[Role] = mapped_column(_enum(Role), default=Role.MEMBER)
    # Relative weight of shared spending: 1 and 1 is 50/50, 3 and 2 is 60/40.
    split_weight: Mapped[int] = mapped_column(default=1)

    household: Mapped[Household] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Set when the owner shares the account into a household.
    household_id: Mapped[int | None] = mapped_column(ForeignKey("households.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="SEK")
    kind: Mapped[AccountKind] = mapped_column(_enum(AccountKind), default=AccountKind.DEBIT, server_default="debit")
    # How uploads are read (spending_core.ImportConfig.to_dict()); saved on each confirmed import.
    import_config: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    owner: Mapped[User] = relationship()
    household: Mapped[Household | None] = relationship()


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    importer: Mapped[str] = mapped_column(String(50))
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64))  # sha256 of the uploaded bytes
    period_start: Mapped[dt.date | None]  # the earliest and latest booking date in the file
    period_end: Mapped[dt.date | None]
    # The month this upload counts toward, as its first day: an upload is one statement,
    # so 27 Sep – 27 Oct is October. Defaults to the month of period_end; can be changed.
    period: Mapped[dt.date | None]
    transaction_count: Mapped[int] = mapped_column(default=0)
    duplicate_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


def _booked_month(context) -> dt.date:
    return context.get_current_parameters()["booked_on"].replace(day=1)


class Transaction(Base):
    __tablename__ = "transactions"
    # NULLs don't collide, so manually added transactions (no hash) are never deduplicated.
    __table_args__ = (UniqueConstraint("account_id", "dedupe_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    import_id: Mapped[int | None] = mapped_column(ForeignKey("imports.id", ondelete="CASCADE"), index=True)
    booked_on: Mapped[dt.date] = mapped_column(index=True)
    # The month it counts toward, as its first day: its upload's period, or for a
    # transaction added by hand, the month it was booked in.
    period: Mapped[dt.date] = mapped_column(index=True, default=_booked_month)
    description_raw: Mapped[str] = mapped_column(String(500))
    description_clean: Mapped[str] = mapped_column(String(500))
    amount_minor: Mapped[int] = mapped_column(BigInteger)  # öre; positive = spending, negative = refund
    currency: Mapped[str] = mapped_column(String(3), default="SEK")
    allocation: Mapped[Allocation] = mapped_column(_enum(Allocation))
    # Whose spending it is when allocation is personal; always null otherwise.
    member_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    category: Mapped[str | None] = mapped_column(String(100))  # a Category name in the account's scope
    # Set by a person rather than by rules; rule changes don't touch it.
    category_manual: Mapped[bool] = mapped_column(default=False, server_default=false())
    # Someone has gone through it and said whose it is (see the statement review).
    reviewed: Mapped[bool] = mapped_column(default=False, server_default=false())
    dedupe_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    account: Mapped[Account] = relationship()


def _one_scope(table: str) -> CheckConstraint:
    return CheckConstraint("(user_id IS NULL) <> (household_id IS NULL)", name=f"ck_{table}_one_scope")


def _unique_per_scope(table: str, *columns: str) -> tuple[Index, Index]:
    """Unique within each user and within each household (partial indexes, on SQLite and Postgres alike)."""
    return tuple(
        Index(f"uq_{table}_{scope}", f"{scope}_id", *columns, unique=True,
              sqlite_where=text(f"{scope}_id IS NOT NULL"), postgresql_where=text(f"{scope}_id IS NOT NULL"))
        for scope in ("user", "household")
    )


class Scoped:
    """Belongs to exactly one of a user or a household."""

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    household_id: Mapped[int | None] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)


class Category(Scoped, Base):
    __tablename__ = "categories"
    __table_args__ = (_one_scope(__tablename__), *_unique_per_scope(__tablename__, "name"))

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # The default category this one started as (spending_core.DEFAULT_CATEGORIES), so
    # the default keywords still find it after a rename. Null for categories users add.
    default_key: Mapped[str | None] = mapped_column(String(100))


class CategoryRule(Scoped, Base):
    __tablename__ = "category_rules"
    __table_args__ = (_one_scope(__tablename__),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern: Mapped[str] = mapped_column(String(200))  # matched case-insensitively within the description
    category: Mapped[str] = mapped_column(String(100))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class Budget(Scoped, Base):
    """A monthly target for a category: every month (month is null) or one month's override."""

    __tablename__ = "budgets"
    __table_args__ = (_one_scope(__tablename__),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100))
    month: Mapped[dt.date | None]  # the first day of the month
    amount_minor: Mapped[int] = mapped_column(BigInteger)


class Settlement(Base):
    """A closed month: the household's settlement as it stood, so later edits don't change history."""

    __tablename__ = "settlements"
    __table_args__ = (UniqueConstraint("household_id", "month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    month: Mapped[dt.date]  # the first day of the month
    result: Mapped[dict] = mapped_column(JSON)  # schemas.Settlement, without closed_at
    closed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    closed_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
