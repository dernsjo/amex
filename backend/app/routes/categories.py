"""Categories, rules and budgets of a scope: yours, or with `?household_id=` a household's.

Any member of a household can change its categories, rules and budgets.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import analysis, categories, models, schemas
from ..access import Scope, scope
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(tags=["categories"])


def _category(c: models.Category) -> schemas.Category:
    return schemas.Category(id=c.id, name=c.name, is_fallback=categories.is_fallback(c))


def _scoped(db: Session, model: type[models.Scoped], id: int, where: Scope, what: str):
    row = db.scalars(select(model).where(model.id == id, where.owns(model))).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")
    return row


def _existing(db: Session, where: Scope, name: str) -> str:
    category = categories.find_category(db, where, name)
    if category is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"No category named {name.strip()!r}")
    return category.name


# Categories


@router.get("/categories", response_model=list[schemas.Category])
def list_categories(where: Scope = Depends(scope), db: Session = Depends(get_db)):
    result = [_category(c) for c in categories.categories(db, where)]
    db.commit()  # the defaults, if this was the first look
    return result


@router.post("/categories", response_model=schemas.Category, status_code=status.HTTP_201_CREATED)
def create_category(data: schemas.CategoryCreate, where: Scope = Depends(scope), db: Session = Depends(get_db)):
    name = data.name.strip()
    if categories.find_category(db, where, name):
        raise HTTPException(status.HTTP_409_CONFLICT, f"There's already a category named {name!r}")
    category = models.Category(name=name, **where.fields())
    db.add(category)
    db.commit()
    return _category(category)


@router.patch("/categories/{category_id}", response_model=schemas.Category)
def rename_category(
    category_id: int, data: schemas.CategoryUpdate, where: Scope = Depends(scope), db: Session = Depends(get_db)
):
    """Rename; the scope's transactions, rules and budgets follow."""
    category = _scoped(db, models.Category, category_id, where, "Category")
    name = data.name.strip()
    other = categories.find_category(db, where, name)
    if other is not None and other is not category:
        raise HTTPException(status.HTTP_409_CONFLICT, f"There's already a category named {name!r}")
    categories.rename(db, where, category, name)
    db.commit()
    return _category(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, where: Scope = Depends(scope), db: Session = Depends(get_db)):
    """Delete with its rules and budgets; its transactions are categorized again by the remaining rules."""
    category = _scoped(db, models.Category, category_id, where, "Category")
    if categories.is_fallback(category):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{category.name} catches everything else; rename it instead")
    categories.delete(db, where, category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Rules


@router.get("/category-rules", response_model=list[schemas.CategoryRule])
def list_rules(where: Scope = Depends(scope), db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(models.CategoryRule)
            .where(where.owns(models.CategoryRule))
            .order_by(models.CategoryRule.category, models.CategoryRule.pattern)
        )
    )


@router.post("/category-rules", response_model=schemas.CategoryRuleResult, status_code=status.HTTP_201_CREATED)
def create_rule(
    data: schemas.CategoryRuleCreate,
    where: Scope = Depends(scope),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """'Always put ICA MAXI in Groceries.' Applies right away to transactions nobody categorized by hand."""
    pattern = " ".join(data.pattern.split())
    category = _existing(db, where, data.category)
    # Compared in Python: SQLite's lower() leaves Å, Ä and Ö alone.
    rules = db.scalars(select(models.CategoryRule).where(where.owns(models.CategoryRule)))
    rule = next((r for r in rules if r.pattern.casefold() == pattern.casefold()), None)
    if rule is None:
        rule = models.CategoryRule(pattern=pattern, created_by_id=user.id, **where.fields())
        db.add(rule)
    rule.category = category
    db.flush()
    changed = categories.recategorize(db, where)
    db.commit()
    return schemas.CategoryRuleResult(rule=schemas.CategoryRule.model_validate(rule), recategorized=changed)


@router.delete("/category-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, where: Scope = Depends(scope), db: Session = Depends(get_db)):
    db.delete(_scoped(db, models.CategoryRule, rule_id, where, "Rule"))
    db.flush()
    categories.recategorize(db, where)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Budgets


@router.get("/budgets", response_model=schemas.BudgetMonth)
def get_budgets(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    where: Scope = Depends(scope),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Each category's target against spending: shared spending for a household, your own share for you."""
    result = analysis.budget_month(db, where, user, categories.month_start(month))
    db.commit()
    return result


@router.put("/budgets", status_code=status.HTTP_204_NO_CONTENT)
def set_budget(data: schemas.BudgetSet, where: Scope = Depends(scope), db: Session = Depends(get_db)):
    """Set a category's target for every month, or with `month` only for that month."""
    category = _existing(db, where, data.category)
    month = categories.month_start(data.month) if data.month else None
    categories.set_budget(db, where, category, month, data.amount_minor)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
