from sqlalchemy.orm import Session
import pandas as pd
from . import models, schemas
from datetime import date

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).filter(models.User.active == True).offset(skip).limit(limit).all()

def get_user_by_name(db: Session, name: str):
    return db.query(models.User).filter(models.User.name == name).first()

def delete_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return

def create_expense(db: Session, expense: schemas.ExpenseCreate):
    db_expense = models.Expense(**expense.model_dump())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

def add_expense(db: Session, expense: schemas.ExpenseBase):
    # Use today's date if no date is provided
    expense_date = expense.date if expense.date else date.today()

    # Default to "Unknown" if paid_by or category is not provided
    db_expense = models.Expense(
        description=expense.description if expense.description else "Unknown",  # Default value
        amount=expense.amount,
        date=expense_date,
        paid_by=expense.paid_by if expense.paid_by else "Unknown",  # Default value
        category=expense.category if expense.category else "General"  # Default value
    )

    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

def create_expenses_batch(db: Session, expenses: list):
    """Create multiple expenses at once"""
    db_expenses = []
    for expense_data in expenses:
        if expense_data.get("amount") is None:
            expense_data["amount"] = 0.0
        expense = models.Expense(**expense_data)
        db.add(expense)
        db_expenses.append(expense)
    db.commit()
    return db_expenses

def get_expense(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Expense).offset(skip).limit(limit).all()

def update_expense_paid_by(db: Session, expense_id: int, paid_by: str):
    """Update the 'paid_by' field for a specific expense"""
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if expense:
        expense.paid_by = paid_by
        db.commit()
        db.refresh(expense)
    return expense

def update_expenses_batch(db: Session, expense_updates: list):
    """Update multiple expenses at once"""
    updated_expenses = []
    for update in expense_updates:
        expense = db.query(models.Expense).filter(models.Expense.id == update.id).first()
        if expense:
            expense.paid_by = update.paid_by
            updated_expenses.append(expense)
    db.commit()
    return updated_expenses


def delete_expense(db: Session, expense_id: int):
    """Delete an expense by its ID"""
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if expense:
        db.delete(expense)
        db.commit()
    return expense