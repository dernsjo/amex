"""Spending for a month or a range of months: yours, or with `?household_id=` a household's.

A household's view counts shared spending; yours counts your own share, as budgets do.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import analysis, models, schemas
from ..access import Scope, scope
from ..auth import get_current_user
from ..categories import month_start
from ..database import get_db

router = APIRouter(tags=["analysis"])

MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.get("/summary", response_model=schemas.Summary)
def get_summary(
    month: str = Query(pattern=MONTH, description="YYYY-MM"),
    where: Scope = Depends(scope),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Each category against its target, the largest spending, and last month's total for comparison."""
    result = analysis.summary(db, where, user, month_start(month))
    db.commit()  # the default categories, if this was the first look
    return result


@router.get("/trends", response_model=schemas.Trends)
def get_trends(
    first: str = Query(alias="from", pattern=MONTH, description="YYYY-MM"),
    last: str = Query(alias="to", pattern=MONTH, description="YYYY-MM, included"),
    where: Scope = Depends(scope),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Spending per month and category, every month in the range."""
    start, end = month_start(first), month_start(last)
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "'to' must not be before 'from'")
    if len(analysis.months(start, end)) > analysis.MAX_TREND_MONTHS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"At most {analysis.MAX_TREND_MONTHS} months")
    return analysis.trends(db, where, user, start, end)
