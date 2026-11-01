from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..access import membership, owner_membership
from ..auth import get_current_user
from ..database import get_db

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
    """Add someone who has signed in at least once. Invitations by link come in Phase 5."""
    hh = owner.household
    user = crud.get_user_by_email(db, data.email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user with that email; they need to sign in once first")
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
def get_settlement(member: models.Membership = Depends(membership), db: Session = Depends(get_db)):
    """Who is responsible for what across the accounts shared into this household."""
    try:
        return crud.settlement(db, member.household)
    except crud.SettlementError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None


def _find_member(hh: models.Household, user_id: int) -> models.Membership:
    target = next((m for m in hh.memberships if m.user_id == user_id), None)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return target


def _only_owner(hh: models.Household, member: models.Membership) -> bool:
    owners = [m for m in hh.memberships if m.role == models.Role.OWNER]
    return owners == [member]
