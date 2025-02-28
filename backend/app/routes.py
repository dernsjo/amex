from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
from datetime import datetime

import crud, models, schemas
from database import get_db

router = APIRouter()

# User routes
@router.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_name(db, name=user.name)
    if db_user:
        raise HTTPException(status_code=400, detail="User already exists")
    return crud.create_user(db=db, user=user)

@router.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/expenses/paid-by-options",response_model=List[str])
def get_paid_by_options(db: Session = Depends(get_db)):
    """Get valid options for the 'paid_by' field"""
    users = crud.get_users(db)
    user_names = [user.name for user in users]
    
    # Always include these options
    standard_options = ["Split", "Outlay", "Exclude"]

    return standard_options + user_names

# Expense routes
@router.post("/expenses/upload/{period}", response_model=List[schemas.Expense])
async def upload_expenses(
    period: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a CSV file with expenses for a specific period"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # First, delete any existing expenses for this period to avoid duplicates
    #existing_expenses = crud.get_expenses_by_period(db, period)
    #for exp in existing_expenses:
    #    db.delete(exp)
    #db.commit()
    
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    
    # Format data if needed (you'll need to implement this based on your format_data method)
    # df = format_data(df)
    
    # Parse date from period if not present in CSV
    year = period[:4]
    month = period[4:]
    default_date = f"{year}-{month}-01"
    
    # Convert DataFrame to ORM objects
    expenses = []
    for _, row in df.iterrows():
        # Handle different column names (Belopp vs amount)
        amount_value = row.get("amount", row.get("Belopp", 0.0))
    
        # Ensure the amount has the correct format (replace comma with dot)
        amount_value = str(amount_value).replace(",", ".")
    
        try:
            # Convert to float after replacing the comma with a dot
            amount_value = float(amount_value)
        except ValueError:
            # Handle invalid float values (e.g., empty or non-numeric)
            amount_value = 0.0

        # Parse the date string into a datetime object
        date_str = row.get("date", default_date)
        try:
            # Convert date from string to datetime.date object
            date_value = datetime.strptime(date_str, "%m-%d-%Y").date()
        except ValueError:
            # If the date format is incorrect, use the default date
            date_value = datetime.strptime(default_date, "%Y-%m-%d").date()
        
        expense_data = {
            "date": date_value,
            "description": row.get("description", ""),
            "amount": amount_value,
            "paid_by": "Split",  # Default to Split
            "category": row.get("category", None)
        }
        expenses.append(expense_data)
    
    # Save expenses to database
    created_expenses = crud.create_expenses_batch(db, expenses)
    
    return created_expenses

@router.get("/expenses/{expense_id}", response_model=schemas.Expense)
def get_single_expense(expense_id: int, db: Session = Depends(get_db)):
    """Get a single expense by its ID"""
    expense = crud.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.put("/expenses/update-paid-by", response_model=List[schemas.Expense])
def update_expenses_paid_by(
    expense_updates: List[schemas.ExpenseUpdate], 
    db: Session = Depends(get_db)
):
    """Update the 'paid_by' field for multiple expenses"""
    updated_expenses = crud.update_expenses_batch(db, expense_updates)
    return updated_expenses

@router.get("/expenses/{period}/calculate", response_model=schemas.CalculationResult)
def calculate_expenses(period: str, db: Session = Depends(get_db)):
    """Calculate who pays what for a specific period"""
    expenses = crud.get_expenses_by_period(db, period)
    users = crud.get_users(db)
    result = crud.calculate_who_pays_what(expenses, users)
    return result

# Save a new expense
@router.post("/expenses/add-expense")
def save_expense(expense: schemas.ExpenseBase, db: Session = Depends(get_db)):
    return crud.add_expense(db, expense)