"""Uyum analizi iş mantığı.

Hibrit yaklaşım:
- V1: deterministik kelime eşleştirme (her zaman çalışır, pure fonksiyon).
- V2: LLM tabanlı semantik analiz (patlarsa V1 yine döner — graceful degradation).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ResourceNotFound
from app.core.logging import get_logger
from app.db.models import CVKaydi, IsIlani, UyumAnalizi
from app.services import gemini
from app.services.cv_service import cv_getir
from app.services.ilan_service import ilan_getir
from app.services.prompts import uyum_semantik_prompt

logger = get_logger(__name__)


def _normalize(beceriler: list) -> set[str]:
    """Beceri listesini karşılaştırma için normalize eder (lower + strip)."""
    return {str(b).lower().strip() for b in beceriler if str(b).strip()}


def uyum_v1_hesapla(
    cv_beceriler: list, gerekli_beceriler: list, tercih_edilen: list
) -> dict:
    """Deterministik kelime eşleştirme. Pure fonksiyon — çekirdek test hedefi.

    Ağırlık: gerekli %70, tercih edilen %30.
    """
    cv_set = _normalize(cv_beceriler)
    gerekli_set = _normalize(gerekli_beceriler)
    tercih_set = _normalize(tercih_edilen)

    eslesen_gerekli = cv_set & gerekli_set
    eksik_gerekli = gerekli_set - cv_set
    eslesen_tercih = cv_set & tercih_set
    ekstra = cv_set - gerekli_set - tercih_set

    gerekli_uyum = (len(eslesen_gerekli) / len(gerekli_set) * 100) if gerekli_set else 0
    tercih_uyum = (len(eslesen_tercih) / len(tercih_set) * 100) if tercih_set else 0

    return {
        "uyum_yuzdesi": round(gerekli_uyum * 0.7 + tercih_uyum * 0.3),
        "gerekli_uyum_yuzdesi": round(gerekli_uyum),
        "tercih_uyum_yuzdesi": round(tercih_uyum),
        "eslesen_gerekli_beceriler": sorted(eslesen_gerekli),
        "eksik_gerekli_beceriler": sorted(eksik_gerekli),
        "eslesen_tercih_edilen": sorted(eslesen_tercih),
        "ekstra_beceriler": sorted(ekstra),
        "hesaplama_yontemi": "kelime_karsilastirma",
    }


def _cv_ve_ilan_getir(
    db: Session, user_id: int, cv_id: int, is_ilani_id: int
) -> tuple[CVKaydi, IsIlani]:
    cv = cv_getir(db, cv_id, user_id)
    if cv is None:
        raise ResourceNotFound(f"CV bulunamadı (id={cv_id}).")
    ilan = ilan_getir(db, is_ilani_id, user_id)
    if ilan is None:
        raise ResourceNotFound(f"İş ilanı bulunamadı (id={is_ilani_id}).")
    return cv, ilan


def uyum_analizi_yap(
    db: Session, user_id: int, cv_id: int, is_ilani_id: int
) -> UyumAnalizi:
    cv, ilan = _cv_ve_ilan_getir(db, user_id, cv_id, is_ilani_id)

    cv_beceriler = (cv.analiz or {}).get("beceriler", []) or []
    gerekli = (ilan.analiz or {}).get("gerekli_beceriler", []) or []
    tercih = (ilan.analiz or {}).get("tercih_edilen_beceriler", []) or []

    v1_sonuc = uyum_v1_hesapla(cv_beceriler, gerekli, tercih)

    # V2 semantik analiz — patlarsa V1'e düş (graceful degradation).
    try:
        v2_sonuc = gemini.json_uret(
            uyum_semantik_prompt(cv_beceriler, gerekli, tercih),
            model=settings.gemini_semantic_model,
        )
        v2_sonuc["hesaplama_yontemi"] = "llm_semantik"
    except Exception as hata:  # noqa: BLE001 — kasıtlı: V2 opsiyonel
        logger.warning("uyum_v2_failed", exc_info=hata)
        v2_sonuc = {
            "hata": "LLM analizi yapılamadı, yalnızca V1 sonucu kullanıldı.",
            "hesaplama_yontemi": "sadece_v1",
        }

    analiz = UyumAnalizi(
        user_id=user_id,
        cv_id=cv.id,
        is_ilani_id=ilan.id,
        v1_sonuc=v1_sonuc,
        v2_sonuc=v2_sonuc,
    )
    db.add(analiz)
    db.commit()
    db.refresh(analiz)
    return analiz


def uyum_gecmis(
    db: Session,
    user_id: int,
    limit: int = 10,
    offset: int = 0,
    cv_id: int | None = None,
    is_ilani_id: int | None = None,
) -> list[UyumAnalizi]:
    stmt = select(UyumAnalizi).where(UyumAnalizi.user_id == user_id)
    if cv_id is not None:
        stmt = stmt.where(UyumAnalizi.cv_id == cv_id)
    if is_ilani_id is not None:
        stmt = stmt.where(UyumAnalizi.is_ilani_id == is_ilani_id)
    stmt = stmt.order_by(UyumAnalizi.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())
