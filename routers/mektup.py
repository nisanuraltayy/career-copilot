from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, CVKaydi, IsIlani, MotivasyonMektubu
from services.gemini_service import gemini_metin_uret

router = APIRouter()


class MotivasyonMektubuIstegi(BaseModel):
    cv_id: int
    is_ilani_id: int


@router.post("/motivasyon-mektubu")
def motivasyon_mektubu_uret(
    istek: MotivasyonMektubuIstegi,
    db: Session = Depends(get_db),
):
    cv = db.query(CVKaydi).filter(CVKaydi.id == istek.cv_id).first()
    if cv is None:
        return {"hata": f"CV bulunamadi (id={istek.cv_id})."}

    ilan = db.query(IsIlani).filter(IsIlani.id == istek.is_ilani_id).first()
    if ilan is None:
        return {"hata": f"Is ilani bulunamadi (id={istek.is_ilani_id})."}

    cv_beceriler = cv.analiz.get("beceriler", []) if cv.analiz else []
    cv_deneyimler = cv.analiz.get("deneyimler", []) if cv.analiz else []
    cv_egitim = cv.analiz.get("egitim", "") if cv.analiz else ""

    pozisyon = ilan.pozisyon_adi
    sirket = ilan.sirket_adi or "ilgili sirket"
    gerekli_beceriler = ilan.analiz.get("gerekli_beceriler", []) if ilan.analiz else []

    prompt = f"""Asagidaki bilgilerle profesyonel ve samimi bir motivasyon mektubu yaz.

ADAY BILGILERI:
- Beceriler: {cv_beceriler}
- Deneyimler: {cv_deneyimler}
- Egitim: {cv_egitim}

BASVURULAN POZISYON:
- Pozisyon: {pozisyon}
- Sirket: {sirket}
- Aranan beceriler: {gerekli_beceriler}

KURALLAR:
- Turkce yaz.
- 200-300 kelime arasi olsun.
- "Sayin Yetkili," ile basla.
- 3-4 paragraf.
- Adayin guclu yonlerini one cikar, ama yalan/abartma yapma.
- "Saygilarimla, [Ad Soyad]" ile bitir.
- Sadece mektup metnini dondur, baska aciklama ekleme.
"""

    try:
        mektup_metni = gemini_metin_uret(prompt)
    except Exception as e:
        return {
            "hata": "Motivasyon mektubu uretilemedi.",
            "teknik_detay": str(e),
        }

    yeni_mektup = MotivasyonMektubu(
        cv_id=cv.id,
        is_ilani_id=ilan.id,
        mektup_metni=mektup_metni,
    )
    db.add(yeni_mektup)
    db.commit()
    db.refresh(yeni_mektup)

    return {
        "id": yeni_mektup.id,
        "cv_id": cv.id,
        "is_ilani_id": ilan.id,
        "pozisyon": pozisyon,
        "sirket": sirket,
        "mektup_metni": mektup_metni,
    }


@router.get("/motivasyon-mektubu-gecmis")
def motivasyon_mektubu_gecmis(
    limit: int = 10,
    cv_id: int | None = None,
    is_ilani_id: int | None = None,
    db: Session = Depends(get_db),
):
    sorgu = db.query(MotivasyonMektubu)

    if cv_id is not None:
        sorgu = sorgu.filter(MotivasyonMektubu.cv_id == cv_id)

    if is_ilani_id is not None:
        sorgu = sorgu.filter(MotivasyonMektubu.is_ilani_id == is_ilani_id)

    mektuplar = (
        sorgu.order_by(MotivasyonMektubu.olusturma_tarihi.desc())
        .limit(limit)
        .all()
    )

    return {
        "toplam_donen": len(mektuplar),
        "mektuplar": [
            {
                "id": m.id,
                "cv_id": m.cv_id,
                "is_ilani_id": m.is_ilani_id,
                "mektup_metni": m.mektup_metni,
                "olusturma_tarihi": m.olusturma_tarihi.isoformat(),
            }
            for m in mektuplar
        ],
    }