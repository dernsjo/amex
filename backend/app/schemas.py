from datetime import date
from typing import Optional
from pydantic import BaseModel

class UserBase(BaseModel):
    name: str
    active: bool = True

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    
    class Config:
        from_attributes = True

class ExpenseBase(BaseModel):
    date: str
    description: str
    amount: float
    paid_by: str = "Split"
    category: Optional[str] = None

    class Config:
        from_attributes = True

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    id: int
    paid_by: str

class Expense(ExpenseBase):
    id: int
    
    class Config:
        from_attributes = True

class CalculationResult(BaseModel):
    expenses: dict[str, float]
    outlay: float
    total: float
    control: float