"""İş ilanı endpoint'leri."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.models import User
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
@limiter.limit(settings.rate_limit_ai)
def is_ilani_analiz(
    request: Request,
    istek: IsIlaniIstegi,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IsIlaniAnalizYaniti:
    ilan = ilan_service.ilan_olustur(db, user_id=user.id, metin=istek.metin)
    return IsIlaniAnalizYaniti(
        id=ilan.id,
        analiz=ilan.analiz,
        embedding_uretildi=ilan.embedding is not None,
    )


@router.get("/is-ilanlari", response_model=IsIlaniListesiYaniti)
def is_ilanlari_listesi(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IsIlaniListesiYaniti:
    ilanlar = ilan_service.ilan_listele(db, user_id=user.id, limit=limit, offset=offset)
    return IsIlaniListesiYaniti(toplam_donen=len(ilanlar), ilanlar=ilanlar)
