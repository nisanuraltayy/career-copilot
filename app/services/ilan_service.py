"""İş ilanı iş mantığı: metin -> analiz -> embedding -> kayıt."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import IsIlani
from app.services import gemini
from app.services.prompts import ilan_analiz_prompt

logger = get_logger(__name__)


def ilan_analizden_embedding_metni(analiz: dict) -> str:
    """İlan analiz JSON'unu embedding için temiz metne çevirir (pure)."""
    parcalar: list[str] = []

    pozisyon = analiz.get("pozisyon_adi")
    if pozisyon:
        parcalar.append("Pozisyon: " + str(pozisyon))

    gerekli = analiz.get("gerekli_beceriler")
    if isinstance(gerekli, list) and gerekli:
        parcalar.append("Gerekli beceriler: " + ", ".join(str(b) for b in gerekli))

    tercih = analiz.get("tercih_edilen_beceriler")
    if isinstance(tercih, list) and tercih:
        parcalar.append("Tercih edilen beceriler: " + ", ".join(str(b) for b in tercih))

    deneyim = analiz.get("deneyim_yili")
    if deneyim:
        parcalar.append("Deneyim: " + str(deneyim))

    return ". ".join(parcalar)


def ilan_olustur(db: Session, metin: str) -> IsIlani:
    analiz = gemini.json_uret(ilan_analiz_prompt(metin))

    embed_metni = ilan_analizden_embedding_metni(analiz)
    embedding = gemini.embedding_uret(embed_metni) if embed_metni else None

    ilan = IsIlani(
        pozisyon_adi=analiz.get("pozisyon_adi") or "Belirtilmemis",
        sirket_adi=analiz.get("sirket_adi"),
        deneyim_yili=analiz.get("deneyim_yili"),
        ham_metin=metin,
        analiz=analiz,
        embedding=embedding,
    )
    db.add(ilan)
    db.commit()
    db.refresh(ilan)
    logger.info(
        "ilan_created",
        extra={"ilan_id": ilan.id, "embedding": embedding is not None},
    )
    return ilan


def ilan_listele(db: Session, limit: int = 10) -> list[IsIlani]:
    stmt = select(IsIlani).order_by(IsIlani.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def ilan_getir(db: Session, ilan_id: int) -> IsIlani | None:
    return db.get(IsIlani, ilan_id)
