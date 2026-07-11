"""İş önerisi endpoint'i (pgvector)."""

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.oneri import OneriYaniti
from app.services import oneri_service

router = APIRouter(tags=["oneri"])


@router.get("/is-onerileri/{cv_id}", response_model=OneriYaniti)
def is_onerileri(
    cv_id: int = Path(..., ge=1),
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OneriYaniti:
    cv, oneriler = oneri_service.is_onerileri(db, user_id=user.id, cv_id=cv_id, limit=limit)
    return OneriYaniti(
        cv_id=cv.id,
        cv_dosya_adi=cv.dosya_adi,
        toplam_oneri=len(oneriler),
        oneriler=oneriler,
    )
