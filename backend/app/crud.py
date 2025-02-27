from sqlalchemy.orm import Session
from .models import Expense

def get_expenses(db: Session, date: str):
    return db.query(Expense).filter(Expense.date == date).all()

def add_expense(db: Session, expense_data):
    expense = Expense(**expense_data)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense