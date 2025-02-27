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

def get_expense(db: Session, expense_id: int):
    return db.query(models.Expense).filter(models.Expense.id == expense_id).first()

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

def calculate_who_pays_what(expenses: list, users: list):
    """Calculate how much each person owes or should be paid back"""
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame([{
        'Belopp': exp.amount,
        'Paid By': exp.paid_by
    } for exp in expenses])
    
    # Remove excluding transactions
    df = df[df['Paid By'] != 'Exclude']

    # Calculate total expenses
    total_expenses = df['Belopp'].sum()

    # Get all user names
    user_names = [user.name for user in users]
    
    # Sum of amounts paid by each user and by "Outlay"
    sum_outlay = df.loc[df['Paid By'] == 'Outlay', 'Belopp'].sum()
    
    # Calculate individual user payments
    user_payments = {}
    for user in user_names:
        user_payments[user] = df.loc[df['Paid By'] == user, 'Belopp'].sum()
    
    # Calculate the remaining amount to be divided equally (Split)
    split_payments = df.loc[df['Paid By'] == 'Split', 'Belopp'].sum()
    equal_share = split_payments / len(user_names) if user_names else 0
    
    # Calculate the final amount each user should pay or receive
    final_amounts = {}
    for user in user_names:
        final_amounts[user] = user_payments.get(user, 0) + equal_share
    
    total_calculated = sum(final_amounts.values()) + sum_outlay
    
    return {
        'expenses': final_amounts,
        'outlay': float(sum_outlay),
        'total': float(total_calculated),
        'control': float(total_expenses)
    }