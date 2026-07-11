"""Motivasyon mektubu endpoint'leri."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.models import User
from app.db.session import get_db
from app.schemas.mektup import (
    MektupListesiYaniti,
    MotivasyonMektubuIstegi,
    MotivasyonMektubuYaniti,
)
from app.services import mektup_service

router = APIRouter(tags=["mektup"])


@router.post(
    "/motivasyon-mektubu",
    response_model=MotivasyonMektubuYaniti,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_ai)
def motivasyon_mektubu_uret(
    request: Request,
    istek: MotivasyonMektubuIstegi,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MotivasyonMektubuYaniti:
    mektup = mektup_service.mektup_uret(
        db, user_id=user.id, cv_id=istek.cv_id, is_ilani_id=istek.is_ilani_id
    )
    return MotivasyonMektubuYaniti(
        id=mektup.id,
        cv_id=mektup.cv_id,
        is_ilani_id=mektup.is_ilani_id,
        pozisyon=mektup.ilan.pozisyon_adi,
        sirket=mektup.ilan.sirket_adi or "ilgili şirket",
        mektup_metni=mektup.mektup_metni,
    )


@router.get("/motivasyon-mektubu-gecmis", response_model=MektupListesiYaniti)
def motivasyon_mektubu_gecmis(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cv_id: int | None = None,
    is_ilani_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MektupListesiYaniti:
    mektuplar = mektup_service.mektup_gecmis(
        db, user_id=user.id, limit=limit, offset=offset, cv_id=cv_id, is_ilani_id=is_ilani_id
    )
    return MektupListesiYaniti(toplam_donen=len(mektuplar), mektuplar=mektuplar)
