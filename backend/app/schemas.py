from datetime import date as Date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Special paid-by values besides user names. Replaced by an allocation enum in Phase 1.
STANDARD_PAID_BY = ["Split", "Outlay", "Exclude"]


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    active: bool


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal
    date: Date | None = None  # defaults to today
    paid_by: str = "Split"
    category: str | None = None  # defaults to keyword categorization


class ExpenseUpdate(BaseModel):
    """Fields left out (None) are not changed."""

    id: int
    paid_by: str | None = None
    category: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.paid_by is None and self.category is None:
            raise ValueError("Provide paid_by and/or category")
        return self


class Expense(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: Date
    description: str
    amount: float
    paid_by: str
    category: str | None


class Settlement(BaseModel):
    per_member: dict[str, float]
    outlay: float
    shared: float
    total: float
