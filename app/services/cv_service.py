"""CV iş mantığı: PDF -> analiz -> embedding -> kayıt."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import CVKaydi
from app.services import gemini
from app.services.pdf import pdf_metin_cikar
from app.services.prompts import cv_analiz_prompt

logger = get_logger(__name__)


def cv_analizden_embedding_metni(analiz: dict) -> str:
    """CV analiz JSON'unu embedding için temiz, düz metne çevirir.

    Pure fonksiyon (yan etkisiz) — kolayca birim test edilir. Beklenmedik
    format gelse bile çökmez (defensive).
    """
    parcalar: list[str] = []

    beceriler = analiz.get("beceriler")
    if isinstance(beceriler, list) and beceriler:
        parcalar.append("Beceriler: " + ", ".join(str(b) for b in beceriler))

    deneyimler = analiz.get("deneyimler")
    if isinstance(deneyimler, list) and deneyimler:
        parcalar.append("Deneyimler: " + ", ".join(str(d) for d in deneyimler))

    egitim = analiz.get("egitim")
    if egitim:
        parcalar.append("Egitim: " + str(egitim))

    return ". ".join(parcalar)


def cv_olustur(
    db: Session, user_id: int, dosya_adi: str, pdf_bytes: bytes
) -> CVKaydi:
    """PDF'i işleyip analiz eder, embedding üretir ve kaydeder (kullanıcıya ait).

    PDF geçersizse `ValidationFailed`, Gemini analizi çökerse
    `UpstreamServiceError` fırlatır (merkezi handler'lar HTTP'ye çevirir).
    """
    cikarim = pdf_metin_cikar(pdf_bytes)

    analiz = gemini.json_uret(cv_analiz_prompt(cikarim.metin))

    embed_metni = cv_analizden_embedding_metni(analiz)
    embedding = gemini.embedding_uret(embed_metni) if embed_metni else None

    kayit = CVKaydi(
        user_id=user_id,
        dosya_adi=dosya_adi,
        karakter_sayisi=len(cikarim.metin),
        sayfa_sayisi=cikarim.sayfa_sayisi,
        analiz=analiz,
        embedding=embedding,
    )
    db.add(kayit)
    db.commit()
    db.refresh(kayit)
    logger.info(
        "cv_created",
        extra={"cv_id": kayit.id, "embedding": embedding is not None},
    )
    return kayit


def cv_listele(
    db: Session, user_id: int, limit: int = 10, offset: int = 0
) -> list[CVKaydi]:
    stmt = (
        select(CVKaydi)
        .where(CVKaydi.user_id == user_id)
        .order_by(CVKaydi.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def cv_getir(db: Session, cv_id: int, user_id: int) -> CVKaydi | None:
    """Sadece kullanıcıya ait CV'yi döndürür (yetkisiz erişimi engeller)."""
    return db.scalar(
        select(CVKaydi).where(CVKaydi.id == cv_id, CVKaydi.user_id == user_id)
    )
