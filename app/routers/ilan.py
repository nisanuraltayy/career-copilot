"""İş ilanı endpoint'leri."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ilan import (
    IsIlaniAnalizYaniti,
    IsIlaniIstegi,
    IsIlaniListesiYaniti,
)
from app.services import ilan_service

router = APIRouter(tags=["ilan"])


@router.post(
    "/is-ilani-analiz",
    response_model=IsIlaniAnalizYaniti,
    status_code=status.HTTP_201_CREATED,
)
def is_ilani_analiz(
    istek: IsIlaniIstegi,
    db: Session = Depends(get_db),
) -> IsIlaniAnalizYaniti:
    ilan = ilan_service.ilan_olustur(db, metin=istek.metin)
    return IsIlaniAnalizYaniti(
        id=ilan.id,
        analiz=ilan.analiz,
        embedding_uretildi=ilan.embedding is not None,
    )


@router.get("/is-ilanlari", response_model=IsIlaniListesiYaniti)
def is_ilanlari_listesi(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> IsIlaniListesiYaniti:
    ilanlar = ilan_service.ilan_listele(db, limit=limit)
    return IsIlaniListesiYaniti(toplam_donen=len(ilanlar), ilanlar=ilanlar)
