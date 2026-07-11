"""CV endpoint'leri — ince HTTP katmanı, iş mantığı cv_service'te."""

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import ValidationFailed
from app.core.rate_limit import limiter
from app.db.models import User
from app.db.session import get_db
from app.schemas.cv import CVListesiYaniti, CVYuklemeYaniti
from app.services import cv_service

router = APIRouter(tags=["cv"])


@router.post(
    "/cv-yukle",
    response_model=CVYuklemeYaniti,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_ai)
def cv_yukle(
    request: Request,
    dosya: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CVYuklemeYaniti:
    if dosya.content_type not in ("application/pdf", "application/octet-stream"):
        raise ValidationFailed("Sadece PDF dosyası yükleyebilirsiniz.")

    pdf_bytes = dosya.file.read()
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise ValidationFailed(
            f"Dosya çok büyük (limit {settings.max_upload_bytes // (1024 * 1024)} MB)."
        )

    kayit = cv_service.cv_olustur(
        db, user_id=user.id, dosya_adi=dosya.filename or "isimsiz.pdf", pdf_bytes=pdf_bytes
    )
    return CVYuklemeYaniti(
        id=kayit.id,
        dosya_adi=kayit.dosya_adi,
        sayfa_sayisi=kayit.sayfa_sayisi,
        karakter_sayisi=kayit.karakter_sayisi,
        analiz=kayit.analiz,
        embedding_uretildi=kayit.embedding is not None,
    )


@router.get("/cv-gecmis", response_model=CVListesiYaniti)
def cv_gecmis(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CVListesiYaniti:
    kayitlar = cv_service.cv_listele(db, user_id=user.id, limit=limit, offset=offset)
    return CVListesiYaniti(toplam_donen=len(kayitlar), kayitlar=kayitlar)
