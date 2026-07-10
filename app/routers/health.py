"""Sağlık ve kök endpoint'leri.

- `/saglik` : liveness — süreç ayakta mı? (bağımlılık kontrol etmez)
- `/hazir`  : readiness — DB dahil bağımlılıklar hazır mı? (yük dengeleyici/K8s
  bu endpoint'e bakarak trafiği yönlendirir)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(tags=["saglik"])
logger = get_logger(__name__)


@router.get("/", response_model=HealthResponse)
def ana_sayfa() -> HealthResponse:
    return HealthResponse(
        durum="calisiyor", surum=settings.app_version, ortam=settings.environment
    )


@router.get("/saglik", response_model=HealthResponse)
def saglik_kontrolu() -> HealthResponse:
    return HealthResponse(
        durum="iyi", surum=settings.app_version, ortam=settings.environment
    )


@router.get(
    "/hazir",
    response_model=ReadinessResponse,
    responses={503: {"description": "Bağımlılık hazır değil"}},
)
def hazirlik_kontrolu(db: Session = Depends(get_db)) -> ReadinessResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception as hata:  # noqa: BLE001
        logger.error("readiness_db_failed", exc_info=hata)
        raise HTTPException(status_code=503, detail="Veritabanına ulaşılamıyor.") from hata
    return ReadinessResponse(durum="hazir", veritabani="baglı")
