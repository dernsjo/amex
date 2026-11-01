from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=schemas.Me)
def get_me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.me(db, user)


@router.patch("", response_model=schemas.Me)
def update_me(
    update: schemas.MeUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.display_name = update.display_name.strip()
    db.commit()
    return crud.me(db, user)
