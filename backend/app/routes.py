from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from spending_core import (
    DEFAULT_CATEGORIES,
    ImportFileError,
    Line,
    allocation_from_label,
    format_minor,
    parse_amex_csv,
    settle,
    to_minor,
)
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


# Users

@router.get("/users", response_model=list[schemas.User])
def list_users(db: Session = Depends(get_db)):
    return crud.get_users(db)


@router.post("/users", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    name = user.name.strip()
    if name.lower() in (o.lower() for o in schemas.STANDARD_PAID_BY):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"'{name}' is a reserved name")
    existing = crud.get_user_by_name(db, name)
    if existing and existing.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "User already exists")
    return crud.create_or_reactivate_user(db, name)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user or not user.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if crud.has_expenses_paid_by(db, user.name):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{user.name} has personal expenses; reassign them before removing the user",
        )
    crud.deactivate_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Expenses

@router.get("/expenses", response_model=list[schemas.Expense])
def list_expenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    return crud.get_expenses(db, skip=skip, limit=limit)


@router.get("/expenses/paid-by-options", response_model=list[str])
def get_paid_by_options(db: Session = Depends(get_db)):
    return crud.paid_by_options(db)


@router.get("/expenses/categories", response_model=list[str])
def get_categories():
    return DEFAULT_CATEGORIES


@router.post("/expenses", response_model=schemas.Expense, status_code=status.HTTP_201_CREATED)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    _validate_paid_by(db, [expense.paid_by])
    if expense.category is not None:
        _validate_categories([expense.category])
    return crud.create_expense(db, expense)


@router.patch("/expenses", response_model=list[schemas.Expense])
def update_expenses(updates: list[schemas.ExpenseUpdate], db: Session = Depends(get_db)):
    """Update 'paid_by' and/or 'category' for one or more expenses, all or nothing."""
    missing = [u.id for u in updates if crud.get_expense(db, u.id) is None]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Expense(s) not found: {missing}")
    _validate_paid_by(db, [u.paid_by for u in updates if u.paid_by is not None])
    _validate_categories([u.category for u in updates if u.category is not None])
    return crud.update_expenses(db, updates)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = crud.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    crud.delete_expense(db, expense)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/expenses/upload", response_model=list[schemas.Expense], status_code=status.HTTP_201_CREATED)
async def upload_expenses(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import an Amex CSV export."""
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is larger than 5 MB")
    try:
        transactions = parse_amex_csv(contents)
    except ImportFileError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
    return crud.create_expenses_from_import(db, transactions)


@router.get("/expenses/settlement", response_model=schemas.Settlement)
def get_settlement(db: Session = Depends(get_db)):
    """Who pays what across all stored expenses, split evenly between active users."""
    members = [u.name for u in crud.get_users(db)]
    if not members:
        raise HTTPException(status.HTTP_409_CONFLICT, "Add at least one user before calculating")

    lines = []
    for e in crud.get_expenses(db):
        try:
            allocation, member = allocation_from_label(e.paid_by, members)
        except ValueError as err:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Expense {e.id}: {err}") from None
        lines.append(Line(to_minor(e.amount), allocation, member))

    result = settle(lines, dict.fromkeys(members, 1))
    return schemas.Settlement(
        per_member={m: float(format_minor(v)) for m, v in result.per_member.items()},
        outlay=float(format_minor(result.outlay)),
        shared=float(format_minor(result.shared)),
        total=float(format_minor(result.total)),
    )


def _validate_paid_by(db: Session, values: list[str]) -> None:
    _validate_choice("paid_by", values, crud.paid_by_options(db))


def _validate_categories(values: list[str]) -> None:
    _validate_choice("category", values, DEFAULT_CATEGORIES)


def _validate_choice(field: str, values: list[str], options: list[str]) -> None:
    invalid = sorted({v for v in values if v not in options})
    if invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid {field} {invalid}; expected one of {options}",
        )
