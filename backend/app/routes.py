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

@router.post("/expenses/upload", response_model=List[schemas.Expense])
async def upload_expenses(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a CSV file with expenses."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    
    expenses = []
    for _, row in df.iterrows():
        amount_value = row.get("Belopp", 0.0)
        amount_value = str(amount_value).replace(",", ".")
        try:
            amount_value = float(amount_value)
        except ValueError:
            amount_value = 0.0 
        
        date_str = row.get("Datum", datetime.today())

        expense_data = {
            "date": date_str,
            "description": row.get("Beskrivning", ""),
            "amount": amount_value,
            "paid_by": "Split",
            "category": row.get("category", None)
        }
        expenses.append(expense_data)
    
    return crud.create_expenses_batch(db, expenses)

@router.get("/expenses/", response_model=List[schemas.Expense])
def get_expense_list(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get a single expense by its ID"""
    expenses = crud.get_expense(db, skip=skip, limit=limit)
    if not expenses:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expenses

@router.put("/expenses/update-paid-by", response_model=List[schemas.Expense])
def update_expenses_paid_by(
    expense_updates: List[schemas.ExpenseUpdate], 
    db: Session = Depends(get_db)
):
    """Update the 'paid_by' field for multiple expenses"""
    updated_expenses = crud.update_expenses_batch(db, expense_updates)
    return updated_expenses

@router.get("/expenses/calculate", response_model=schemas.CalculationResult)
def calculate_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Calculate who pays what for specific transactions"""
    expenses = crud.get_expense(db, skip, limit)
    users = crud.get_users(db)
    result = crud.calculate_who_pays_what(expenses, users)
    return result

# Save a new expense
@router.post("/expenses/add-expense")
def save_expense(expense: schemas.ExpenseBase, db: Session = Depends(get_db)):
    return crud.add_expense(db, expense)

# Delete an expense
@router.delete("/expenses/{expense_id}")
def delete_expense_route(expense_id: int, db: Session = Depends(get_db)):
    return crud.delete_expense(db, expense_id)