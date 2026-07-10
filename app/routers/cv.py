"""CV endpoint'leri — ince HTTP katmanı, iş mantığı cv_service'te."""

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ValidationFailed
from app.db.session import get_db
from app.schemas.cv import CVListesiYaniti, CVYuklemeYaniti
from app.services import cv_service

router = APIRouter(tags=["cv"])


@router.post(
    "/cv-yukle",
    response_model=CVYuklemeYaniti,
    status_code=status.HTTP_201_CREATED,
)
def cv_yukle(
    dosya: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CVYuklemeYaniti:
    if dosya.content_type not in ("application/pdf", "application/octet-stream"):
        raise ValidationFailed("Sadece PDF dosyası yükleyebilirsiniz.")

    pdf_bytes = dosya.file.read()
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise ValidationFailed(
            f"Dosya çok büyük (limit {settings.max_upload_bytes // (1024 * 1024)} MB)."
        )

    kayit = cv_service.cv_olustur(
        db, dosya_adi=dosya.filename or "isimsiz.pdf", pdf_bytes=pdf_bytes
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
    db: Session = Depends(get_db),
) -> CVListesiYaniti:
    kayitlar = cv_service.cv_listele(db, limit=limit)
    return CVListesiYaniti(toplam_donen=len(kayitlar), kayitlar=kayitlar)
