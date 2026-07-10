"""Motivasyon mektubu endpoint'leri."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

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
def motivasyon_mektubu_uret(
    istek: MotivasyonMektubuIstegi,
    db: Session = Depends(get_db),
) -> MotivasyonMektubuYaniti:
    mektup = mektup_service.mektup_uret(db, istek.cv_id, istek.is_ilani_id)
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
    cv_id: int | None = None,
    is_ilani_id: int | None = None,
    db: Session = Depends(get_db),
) -> MektupListesiYaniti:
    mektuplar = mektup_service.mektup_gecmis(
        db, limit=limit, cv_id=cv_id, is_ilani_id=is_ilani_id
    )
    return MektupListesiYaniti(toplam_donen=len(mektuplar), mektuplar=mektuplar)
