from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base
from .crud import get_expenses, add_expense

# Create database tables
Base.metadata.create_all(bind=engine)

router = APIRouter()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Load expenses for a given date
@router.get("/expenses/{date}")
def load_expenses(date: str, db: Session = Depends(get_db)):
    expenses = get_expenses(db, date)
    if not expenses:
        raise HTTPException(status_code=404, detail="No data found")
    return expenses

# Save a new expense
@router.post("/expenses")
def save_expense(expense: dict, db: Session = Depends(get_db)):
    return add_expense(db, expense)