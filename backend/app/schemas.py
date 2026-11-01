from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator
from spending_core import Allocation

from .models import AccountKind, Role


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# A month as YYYY-MM, read from the first day of the month as stored.
MonthLabel = Annotated[str, BeforeValidator(lambda v: v.strftime("%Y-%m") if isinstance(v, Date) else v)]


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
    pending: bool  # added by email but hasn't signed in yet


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class HouseholdUpdate(HouseholdCreate):
    pass


class Household(BaseModel):
    id: int
    name: str
    members: list[Member]


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    display_name: str | None = Field(None, min_length=1, max_length=100)  # for someone who hasn't signed in


class MemberUpdate(BaseModel):
    """Fields left out are not changed."""

    split_weight: int | None = Field(None, ge=0, le=1000)
    role: Role | None = None


# Imports


class CsvMapping(BaseModel):
    """Mirrors spending_core.CsvMapping."""

    date_column: str = Field(min_length=1)
    description_column: str = Field(min_length=1)
    amount_column: str = Field(min_length=1)
    decimal_separator: Literal[",", "."] = ","
    spending_is_negative: bool = True
    date_format: str | None = None  # strptime format; None tries the common ones


class ImportConfig(BaseModel):
    """Mirrors spending_core.ImportConfig: a built-in importer id, or "csv" with a mapping."""

    importer: str
    mapping: CsvMapping | None = None


class ImporterInfo(BaseModel):
    id: str
    name: str


class SuggestedMapping(BaseModel):
    """A guess to prefill the mapping form; columns that couldn't be guessed are null."""

    date_column: str | None
    description_column: str | None
    amount_column: str | None
    decimal_separator: Literal[",", "."]
    spending_is_negative: bool
    date_format: str | None


class PreviewTransaction(BaseModel):
    booked_on: Date
    description: str
    amount_minor: int
    category: str
    duplicate: bool  # already imported into this account; skipped on confirm


class ImportPreview(BaseModel):
    filename: str
    # How the file was read and why: "requested" (sent with the upload), "saved"
    # (the account's last config), "detected" (a built-in importer recognized it),
    # "guessed" (columns guessed from the header), or "none".
    config: ImportConfig | None
    source: Literal["requested", "saved", "detected", "guessed", "none"]
    importers: list[ImporterInfo]
    suggested_mapping: SuggestedMapping
    columns: list[str]
    sample_rows: list[list[str]]  # the first raw rows, for choosing columns
    transactions: list[PreviewTransaction]
    new_count: int
    duplicate_count: int
    already_imported_at: datetime | None  # when this exact file was imported before
    period: str | None  # YYYY-MM: the month the upload will count toward
    error: str | None  # why the file couldn't be read with `config`; fix the config and preview again


class ImportResult(Orm):
    id: int
    account_id: int
    importer: str
    filename: str
    period_start: Date | None
    period_end: Date | None
    period: MonthLabel | None  # the month its transactions count toward
    transaction_count: int
    duplicate_count: int
    created_at: datetime


class ImportUpdate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")


# Accounts

class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    currency: str = Field("SEK", min_length=3, max_length=3)
    household_id: int | None = None  # share into this household right away
    kind: AccountKind = AccountKind.DEBIT


class AccountUpdate(BaseModel):
    """Fields left out are not changed; `household_id: null` stops sharing."""

    name: str | None = Field(None, min_length=1, max_length=100)
    household_id: int | None = None
    kind: AccountKind | None = None


class Account(BaseModel):
    id: int
    name: str
    currency: str
    owner: Person
    household_id: int | None
    kind: AccountKind  # debit: paid as spent, by its owner; credit: paid later, one bill per statement
    import_config: ImportConfig | None  # how the next upload will be read
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
    # Checked in a review. Changing allocation or member checks it too, unless this says false.
    reviewed: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.allocation is None and self.member_id is None and self.category is None and self.reviewed is None:
            raise ValueError("Provide allocation, member_id, category and/or reviewed")
        return self


class Transaction(Orm):
    id: int
    account_id: int
    import_id: int | None
    booked_on: Date
    period: MonthLabel  # the month it counts toward: its statement's, or the month it was booked in
    description: str = Field(validation_alias="description_clean")
    amount_minor: int
    currency: str
    allocation: Allocation
    member_id: int | None
    category: str | None
    reviewed: bool  # someone has said whose it is


# Categories and budgets

Name = Field(min_length=1, max_length=100)


class Category(Orm):
    id: int
    name: str
    is_fallback: bool  # where anything unmatched goes; can be renamed but not deleted


class CategoryCreate(BaseModel):
    name: str = Name


class CategoryUpdate(BaseModel):
    name: str = Name


class CategoryRule(Orm):
    id: int
    pattern: str
    category: str


class CategoryRuleCreate(BaseModel):
    pattern: str = Field(min_length=2, max_length=200)
    category: str = Name


class CategoryRuleResult(BaseModel):
    rule: CategoryRule
    recategorized: int  # transactions the rules now put somewhere else


class BudgetSet(BaseModel):
    category: str = Name
    month: str | None = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # YYYY-MM for one month; null for every month
    amount_minor: int | None = Field(None, ge=0)  # null removes the target


class BudgetLine(BaseModel):
    category: str
    recurring_minor: int | None  # the target for every month
    override_minor: int | None  # this month's own target, if set
    target_minor: int | None  # what applies this month
    spent_minor: int


class BudgetMonth(BaseModel):
    month: str  # YYYY-MM
    lines: list[BudgetLine]
    target_minor: int
    spent_minor: int


# Analysis

Month = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")


class Summary(BudgetMonth):
    """A month at a glance: each category against its target, and where the money went."""

    largest: list[Transaction]  # the biggest spending that counts in this view
    previous_spent_minor: int  # the month before, for comparison


class TrendMonth(BaseModel):
    month: str  # YYYY-MM
    spent_minor: int
    by_category: dict[str, int]  # categories with no spending are left out


class Trends(BaseModel):
    months: list[TrendMonth]  # every month in the range, oldest first


class AnalysisCategory(BaseModel):
    category: str
    spent_minor: int
    previous_minor: int  # the month before


class AnalysisMember(Person):
    """What one member is responsible for on the household's accounts: personal purchases plus their part of the shared."""

    amount_minor: int
    by_category: dict[str, int]  # categories with nothing are left out


class Analysis(BaseModel):
    month: str  # YYYY-MM
    spent_minor: int
    previous_spent_minor: int
    categories: list[AnalysisCategory]  # largest first; includes last month's categories with nothing this month
    members: list[AnalysisMember]  # a household's view only


# Settlement

class MemberShare(Person):
    amount_minor: int  # what they're responsible for: their personal spending plus their part of shared
    paid_minor: int  # shared and personal spending on bank accounts they own (credit cards aren't paid yet)
    # Paid minus responsible, for bank-account spending only: positive is owed money, negative owes
    balance_minor: int
    bill_minor: int = 0  # what they pay toward the month's credit card bills


class BillShare(Person):
    amount_minor: int


class Bill(BaseModel):
    """A credit card's statement for the month: nobody has paid it yet, so it's split as what each pays."""

    account_id: int
    account_name: str
    owner: Person
    total_minor: int  # the spending on the statement that the split covers
    outlay_minor: int  # included in the owner's share: they fronted it and are reimbursed outside the split
    shares: list[BillShare]


class Transfer(BaseModel):
    debtor: Person
    creditor: Person
    amount_minor: int


class Unchecked(BaseModel):
    """Transactions in a month that nobody has gone through yet, per statement."""

    account_id: int
    account_name: str
    import_id: int | None  # null: added by hand
    period: MonthLabel | None = None  # the statement's month
    count: int


class StatementReview(BaseModel):
    """Going through one statement: how far along, and what it comes to so far."""

    statement: ImportResult
    account_name: str
    account_kind: AccountKind
    total_count: int
    checked_count: int
    # What each person pays (a card) or is responsible for (a bank account) on this statement alone.
    split: Bill


class Settlement(BaseModel):
    household_id: int
    month: str  # YYYY-MM
    per_member: list[MemberShare]
    transfers: list[Transfer]  # who pays whom to even out the month's bank-account spending
    bills: list[Bill] = []  # how each credit card statement is split
    unchecked: list[Unchecked] = []  # transactions in the month nobody has gone through yet
    outlay_minor: int
    shared_minor: int
    total_minor: int
    closed_at: datetime | None = None  # set when this is a closed month's stored result


class SettlementClose(BaseModel):
    month: str = Month
