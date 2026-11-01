"""Database tables.

Data belongs to users: a user owns accounts, and transactions belong to an
account. A household is optional; an owner can share an account into one, which
lets the other members see and allocate its transactions. Access is therefore
always "accounts I own, or accounts shared into a household I'm a member of"
(see access.py).
"""

import datetime as dt
from enum import StrEnum

from spending_core import Allocation
from sqlalchemy import BigInteger, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


def _enum(enum_class: type[StrEnum]) -> Enum:
    # Stored as plain strings (no Postgres ENUM type), so adding a value needs no migration.
    return Enum(enum_class, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True)  # Supabase user id (JWT `sub`)
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
    period_start: Mapped[dt.date | None]
    period_end: Mapped[dt.date | None]
    transaction_count: Mapped[int] = mapped_column(default=0)
    duplicate_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"
    # NULLs don't collide, so manually added transactions (no hash) are never deduplicated.
    __table_args__ = (UniqueConstraint("account_id", "dedupe_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    import_id: Mapped[int | None] = mapped_column(ForeignKey("imports.id", ondelete="CASCADE"), index=True)
    booked_on: Mapped[dt.date] = mapped_column(index=True)
    description_raw: Mapped[str] = mapped_column(String(500))
    description_clean: Mapped[str] = mapped_column(String(500))
    amount_minor: Mapped[int] = mapped_column(BigInteger)  # öre; positive = spending, negative = refund
    currency: Mapped[str] = mapped_column(String(3), default="SEK")
    allocation: Mapped[Allocation] = mapped_column(_enum(Allocation))
    # Whose spending it is when allocation is personal; always null otherwise.
    member_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    category: Mapped[str | None] = mapped_column(String(100))  # becomes a Category FK in Phase 3
    dedupe_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    account: Mapped[Account] = relationship()
