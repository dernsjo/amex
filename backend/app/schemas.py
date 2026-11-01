from datetime import date as Date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from spending_core import Allocation

from .models import Role


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Users and households

class HouseholdSummary(BaseModel):
    id: int
    name: str
    role: Role


class Me(BaseModel):
    id: int
    email: str
    display_name: str
    households: list[HouseholdSummary]


class MeUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


class Person(BaseModel):
    user_id: int
    display_name: str


class Member(Person):
    email: str
    role: Role
    split_weight: int


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class HouseholdUpdate(HouseholdCreate):
    pass


class Household(BaseModel):
    id: int
    name: str
    members: list[Member]


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class MemberUpdate(BaseModel):
    """Fields left out are not changed."""

    split_weight: int | None = Field(None, ge=0, le=1000)
    role: Role | None = None


# Accounts

class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    currency: str = Field("SEK", min_length=3, max_length=3)
    household_id: int | None = None  # share into this household right away


class AccountUpdate(BaseModel):
    """Fields left out are not changed; `household_id: null` stops sharing."""

    name: str | None = Field(None, min_length=1, max_length=100)
    household_id: int | None = None


class Account(BaseModel):
    id: int
    name: str
    currency: str
    owner: Person
    household_id: int | None
    # Who a transaction on this account can be marked as personal for.
    members: list[Person]


# Transactions

class TransactionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal  # kronor, as typed by the user
    booked_on: Date | None = None  # defaults to today
    allocation: Allocation | None = None  # defaults to shared on a shared account, else personal
    member_id: int | None = None
    category: str | None = None  # defaults to keyword categorization


class TransactionUpdate(BaseModel):
    """Fields left out are not changed. Setting member_id implies a personal allocation."""

    id: int
    allocation: Allocation | None = None
    member_id: int | None = None
    category: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.allocation is None and self.member_id is None and self.category is None:
            raise ValueError("Provide allocation, member_id and/or category")
        return self


class Transaction(Orm):
    id: int
    account_id: int
    import_id: int | None
    booked_on: Date
    description: str = Field(validation_alias="description_clean")
    amount_minor: int
    currency: str
    allocation: Allocation
    member_id: int | None
    category: str | None


class ImportResult(Orm):
    id: int
    account_id: int
    filename: str
    transaction_count: int
    duplicate_count: int


# Settlement

class MemberShare(Person):
    amount_minor: int


class Settlement(BaseModel):
    household_id: int
    per_member: list[MemberShare]
    outlay_minor: int
    shared_minor: int
    total_minor: int
