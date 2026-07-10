"""Uyum analizi endpoint'leri."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.uyum import (
    UyumAnaliziIstegi,
    UyumAnaliziListesiYaniti,
    UyumAnaliziYaniti,
)
from app.services import uyum_service

router = APIRouter(tags=["uyum"])


@router.post(
    "/uyum-analizi",
    response_model=UyumAnaliziYaniti,
    status_code=status.HTTP_201_CREATED,
)
def uyum_analizi(
    istek: UyumAnaliziIstegi,
    db: Session = Depends(get_db),
) -> UyumAnaliziYaniti:
    analiz = uyum_service.uyum_analizi_yap(db, istek.cv_id, istek.is_ilani_id)
    return UyumAnaliziYaniti(
        id=analiz.id,
        cv_id=analiz.cv_id,
        is_ilani_id=analiz.is_ilani_id,
        v1_basit=analiz.v1_sonuc,
        v2_llm=analiz.v2_sonuc,
    )


@router.get("/uyum-analizi-gecmis", response_model=UyumAnaliziListesiYaniti)
def uyum_analizi_gecmis(
    limit: int = Query(10, ge=1, le=100),
    cv_id: int | None = None,
    is_ilani_id: int | None = None,
    db: Session = Depends(get_db),
) -> UyumAnaliziListesiYaniti:
    analizler = uyum_service.uyum_gecmis(
        db, limit=limit, cv_id=cv_id, is_ilani_id=is_ilani_id
    )
    return UyumAnaliziListesiYaniti(toplam_donen=len(analizler), analizler=analizler)
