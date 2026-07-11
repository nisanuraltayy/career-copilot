"""Uyum analizi endpoint'leri."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.models import User
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
@limiter.limit(settings.rate_limit_ai)
def uyum_analizi(
    request: Request,
    istek: UyumAnaliziIstegi,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UyumAnaliziYaniti:
    analiz = uyum_service.uyum_analizi_yap(
        db, user_id=user.id, cv_id=istek.cv_id, is_ilani_id=istek.is_ilani_id
    )
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
    offset: int = Query(0, ge=0),
    cv_id: int | None = None,
    is_ilani_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UyumAnaliziListesiYaniti:
    analizler = uyum_service.uyum_gecmis(
        db, user_id=user.id, limit=limit, offset=offset, cv_id=cv_id, is_ilani_id=is_ilani_id
    )
    return UyumAnaliziListesiYaniti(toplam_donen=len(analizler), analizler=analizler)
