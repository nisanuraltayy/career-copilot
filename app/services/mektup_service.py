"""Motivasyon mektubu iş mantığı."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFound
from app.db.models import MotivasyonMektubu
from app.services import gemini
from app.services.cv_service import cv_getir
from app.services.ilan_service import ilan_getir
from app.services.prompts import motivasyon_mektubu_prompt


def mektup_uret(db: Session, cv_id: int, is_ilani_id: int) -> MotivasyonMektubu:
    cv = cv_getir(db, cv_id)
    if cv is None:
        raise ResourceNotFound(f"CV bulunamadı (id={cv_id}).")
    ilan = ilan_getir(db, is_ilani_id)
    if ilan is None:
        raise ResourceNotFound(f"İş ilanı bulunamadı (id={is_ilani_id}).")

    cv_analiz = cv.analiz or {}
    prompt = motivasyon_mektubu_prompt(
        beceriler=cv_analiz.get("beceriler", []),
        deneyimler=cv_analiz.get("deneyimler", []),
        egitim=cv_analiz.get("egitim", ""),
        pozisyon=ilan.pozisyon_adi,
        sirket=ilan.sirket_adi or "ilgili şirket",
        gerekli_beceriler=(ilan.analiz or {}).get("gerekli_beceriler", []),
    )

    mektup_metni = gemini.metin_uret(prompt)

    mektup = MotivasyonMektubu(
        cv_id=cv.id,
        is_ilani_id=ilan.id,
        mektup_metni=mektup_metni,
    )
    db.add(mektup)
    db.commit()
    db.refresh(mektup)
    return mektup


def mektup_gecmis(
    db: Session,
    limit: int = 10,
    cv_id: int | None = None,
    is_ilani_id: int | None = None,
) -> list[MotivasyonMektubu]:
    stmt = select(MotivasyonMektubu)
    if cv_id is not None:
        stmt = stmt.where(MotivasyonMektubu.cv_id == cv_id)
    if is_ilani_id is not None:
        stmt = stmt.where(MotivasyonMektubu.is_ilani_id == is_ilani_id)
    stmt = stmt.order_by(MotivasyonMektubu.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())
