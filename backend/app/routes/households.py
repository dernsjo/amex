from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from .. import analysis, crud, models, schemas
from ..access import membership, owner_membership
from ..auth import get_current_user
from ..categories import month_start
from ..database import get_db
from .analysis import MONTH

router = APIRouter(prefix="/households", tags=["households"])


@router.post("", response_model=schemas.Household, status_code=status.HTTP_201_CREATED)
def create_household(
    data: schemas.HouseholdCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.household(crud.create_household(db, user, data.name.strip()))


@router.get("/{household_id}", response_model=schemas.Household)
def get_household(member: models.Membership = Depends(membership)):
    return crud.household(member.household)


@router.patch("/{household_id}", response_model=schemas.Household)
def update_household(
    data: schemas.HouseholdUpdate,
    owner: models.Membership = Depends(owner_membership),
    db: Session = Depends(get_db),
):
    owner.household.name = data.name.strip()
    db.commit()
    return crud.household(owner.household)


@router.post("/{household_id}/members", response_model=schemas.Household, status_code=status.HTTP_201_CREATED)
def add_member(
    data: schemas.MemberAdd,
    owner: models.Membership = Depends(owner_membership),
    db: Session = Depends(get_db),
):
    """Add someone by email. If they haven't signed in yet they're added as a pending
    member, who can be split with right away and takes over the membership on first sign-in."""
    hh = owner.household
    email = data.email.strip()
    user = crud.get_user_by_email(db, email)
    if user is None:
        user = models.User(email=email, display_name=(data.display_name or email.split("@")[0]).strip())
    if any(m.user_id == user.id for m in hh.memberships):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{user.display_name} is already a member")
    hh.memberships.append(models.Membership(user=user, role=models.Role.MEMBER))
    db.commit()
    return crud.household(hh)


@router.patch("/{household_id}/members/{user_id}", response_model=schemas.Household)
def update_member(
    user_id: int,
    data: schemas.MemberUpdate,
    owner: models.Membership = Depends(owner_membership),
    db: Session = Depends(get_db),
):
    hh = owner.household
    target = _find_member(hh, user_id)
    if data.split_weight is not None:
        target.split_weight = data.split_weight
    if data.role is not None:
        if data.role != models.Role.OWNER and _only_owner(hh, target):
            raise HTTPException(status.HTTP_409_CONFLICT, "A household needs at least one owner")
        target.role = data.role
    db.commit()
    return crud.household(hh)


@router.delete("/{household_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    me: models.Membership = Depends(membership),
    db: Session = Depends(get_db),
):
    """Owners can remove anyone; members can only leave."""
    hh = me.household
    target = _find_member(hh, user_id)
    if target is not me and me.role != models.Role.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a household owner can remove other members")
    if _only_owner(hh, target) and len(hh.memberships) > 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "Make someone else an owner before leaving")
    crud.remove_member(db, target)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{household_id}/settlement", response_model=schemas.Settlement)
def get_settlement(
    month: str = Query(pattern=MONTH, description="YYYY-MM"),
    member: models.Membership = Depends(membership),
    db: Session = Depends(get_db),
):
    """Who is responsible for what in a month, and who pays whom; a closed month answers what was stored."""
    try:
        return analysis.settlement(db, member.household, month_start(month))
    except analysis.SettlementError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None


@router.get("/{household_id}/settlements", response_model=list[schemas.Settlement])
def list_settlements(member: models.Membership = Depends(membership), db: Session = Depends(get_db)):
    """Closed months, newest first."""
    return analysis.closed_months(db, member.household_id)


@router.post("/{household_id}/settlements", response_model=schemas.Settlement, status_code=status.HTTP_201_CREATED)
def close_month(
    data: schemas.SettlementClose,
    member: models.Membership = Depends(membership),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Close a month: its settlement is stored as it is now, and later edits don't change it."""
    month = month_start(data.month)
    if analysis.closed_month(db, member.household_id, month) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{data.month} is already closed")
    try:
        return analysis.close_month(db, member.household, user, month)
    except analysis.SettlementError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None


@router.delete("/{household_id}/settlements/{month}", status_code=status.HTTP_204_NO_CONTENT)
def reopen_month(
    month: str = Path(pattern=MONTH, description="YYYY-MM"),
    owner: models.Membership = Depends(owner_membership),
    db: Session = Depends(get_db),
):
    """Reopen a closed month: its settlement is worked out from the transactions again."""
    closed = analysis.closed_month(db, owner.household_id, month_start(month))
    if closed is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{month} isn't closed")
    db.delete(closed)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _find_member(hh: models.Household, user_id: int) -> models.Membership:
    target = next((m for m in hh.memberships if m.user_id == user_id), None)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return target


def _only_owner(hh: models.Household, member: models.Membership) -> bool:
    owners = [m for m in hh.memberships if m.role == models.Role.OWNER]
    return owners == [member]
