"""İş önerisi iş mantığı — pgvector cosine distance ile eşleştirme."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ResourceNotFound
from app.db.models import CVKaydi, IsIlani
from app.services.cv_service import cv_getir


def is_onerileri(
    db: Session, user_id: int, cv_id: int, limit: int = 5
) -> tuple[CVKaydi, list[dict]]:
    """CV'ye en yakın ilanları pgvector cosine distance (<=>) ile sıralar.

    Hesap veritabanı katmanında yapılır; tüm vektörler Python'a çekilmez
    (ölçeklenebilir yaklaşım). Sadece kullanıcının kendi, embedding'i olan
    ilanları dikkate alınır (multi-tenant izolasyon).
    """
    cv = cv_getir(db, cv_id, user_id)
    if cv is None:
        raise ResourceNotFound(f"CV bulunamadı (id={cv_id}).")
    if cv.embedding is None:
        raise BusinessRuleError(
            f"Bu CV'nin embedding'i yok, öneri hesaplanamaz (id={cv_id})."
        )

    uzaklik = IsIlani.embedding.cosine_distance(cv.embedding).label("uzaklik")
    stmt = (
        select(IsIlani, uzaklik)
        .where(IsIlani.user_id == user_id, IsIlani.embedding.isnot(None))
        .order_by(uzaklik)
        .limit(limit)
    )

    oneriler: list[dict] = []
    for ilan, mesafe in db.execute(stmt).all():
        benzerlik = 1 - mesafe
        oneriler.append(
            {
                "ilan_id": ilan.id,
                "pozisyon_adi": ilan.pozisyon_adi,
                "sirket_adi": ilan.sirket_adi,
                "deneyim_yili": ilan.deneyim_yili,
                "uyum_skoru": round(benzerlik * 100, 1),
                "uzaklik": round(mesafe, 4),
            }
        )

    return cv, oneriler
