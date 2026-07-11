"""Motivasyon mektubu iş mantığı.

Not (kök-neden koruması): mektup prompt'u, CV analizinden gelen `beceriler` ve
`deneyimler` listelerini olduğu gibi gömüyordu — sınır yoktu. Anormal büyük bir
analiz (örn. çok uzun deneyim metinleri) prompt'u şişirip upstream'de kararsızlığa
(timeout/503) katkı yapabilir. Aşağıdaki sınırlar prompt'u öngörülebilir ve
güvenli bir boyutta tutar; kırpma olursa loglanır.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFound
from app.core.logging import get_logger
from app.db.models import MotivasyonMektubu
from app.services import gemini
from app.services.cv_service import cv_getir
from app.services.ilan_service import ilan_getir
from app.services.prompts import motivasyon_mektubu_prompt

logger = get_logger(__name__)

# Prompt'a girecek analiz verisi için üst sınırlar (akıllı kırpma).
MAX_BECERI = 40
MAX_DENEYIM = 20
MAX_DENEYIM_UZUNLUK = 200  # karakter/öğe
MAX_EGITIM_UZUNLUK = 500  # karakter


def _kirp_liste(ogeler: object, azami: int) -> list[str]:
    """Listeyi ilk `azami` öğeye indirger; öğeleri string'e çevirir."""
    if not isinstance(ogeler, list):
        return []
    return [str(o) for o in ogeler[:azami]]


def _kirp_metin(metin: object, azami: int) -> str:
    """Metni `azami` karaktere kırpar (kelime sınırında değil, güvenli üst-kaba)."""
    s = str(metin or "").strip()
    return s if len(s) <= azami else s[:azami].rstrip() + "…"


def mektup_uret(db: Session, cv_id: int, is_ilani_id: int) -> MotivasyonMektubu:
    cv = cv_getir(db, cv_id)
    if cv is None:
        raise ResourceNotFound(f"CV bulunamadı (id={cv_id}).")
    ilan = ilan_getir(db, is_ilani_id)
    if ilan is None:
        raise ResourceNotFound(f"İş ilanı bulunamadı (id={is_ilani_id}).")

    cv_analiz = cv.analiz or {}
    ham_beceriler = cv_analiz.get("beceriler", []) or []
    ham_deneyimler = cv_analiz.get("deneyimler", []) or []

    # Akıllı kırpma: listeleri ve uzun metinleri güvenli sınıra indir.
    beceriler = _kirp_liste(ham_beceriler, MAX_BECERI)
    deneyimler = [
        _kirp_metin(d, MAX_DENEYIM_UZUNLUK)
        for d in _kirp_liste(ham_deneyimler, MAX_DENEYIM)
    ]
    egitim = _kirp_metin(cv_analiz.get("egitim", ""), MAX_EGITIM_UZUNLUK)
    gerekli_beceriler = _kirp_liste(
        (ilan.analiz or {}).get("gerekli_beceriler", []) or [], MAX_BECERI
    )

    _beceri_asildi = isinstance(ham_beceriler, list) and len(ham_beceriler) > MAX_BECERI
    _deneyim_asildi = (
        isinstance(ham_deneyimler, list) and len(ham_deneyimler) > MAX_DENEYIM
    )
    if _beceri_asildi or _deneyim_asildi:
        logger.warning(
            "mektup_input_truncated",
            extra={
                "cv_id": cv.id,
                "beceri_ham": len(ham_beceriler) if isinstance(ham_beceriler, list) else 0,
                "beceri_kirpik": len(beceriler),
                "deneyim_ham": len(ham_deneyimler) if isinstance(ham_deneyimler, list) else 0,
                "deneyim_kirpik": len(deneyimler),
            },
        )

    prompt = motivasyon_mektubu_prompt(
        beceriler=beceriler,
        deneyimler=deneyimler,
        egitim=egitim,
        pozisyon=ilan.pozisyon_adi,
        sirket=ilan.sirket_adi or "ilgili şirket",
        gerekli_beceriler=gerekli_beceriler,
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
