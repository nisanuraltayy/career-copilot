from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, IsIlani
from services.gemini_service import gemini_json_uret

router = APIRouter()


class IsIlaniIstegi(BaseModel):
    metin: str


@router.post("/is-ilani-analiz")
def is_ilani_analiz(
    istek: IsIlaniIstegi,
    db: Session = Depends(get_db),
):
    metin = istek.metin.strip()
    if not metin:
        return {"hata": "Is ilani metni bos olamaz."}

    prompt = f"""Asagida bir is ilani metni var. Bu ilandan asagidaki bilgileri JSON formatinda cikar:
- pozisyon_adi (string): orn. "Backend Developer"
- sirket_adi (string ya da null): belirtilmemisse null
- deneyim_yili (string ya da null): orn. "2-3 yil", "junior", "5+ yil". Belirtilmemisse null
- gerekli_beceriler (liste): mutlaka aranan beceriler (must-have)
- tercih_edilen_beceriler (liste): nice-to-have, plus olan beceriler

Sadece JSON dondur, baska aciklama ekleme.

IS ILANI METNI:
{metin}
"""

    try:
        ilan_analizi = gemini_json_uret(prompt)
    except Exception as e:
        return {
            "hata": "Is ilani analizi yapilamadi.",
            "teknik_detay": str(e),
        }

    yeni_ilan = IsIlani(
        pozisyon_adi=ilan_analizi.get("pozisyon_adi", "Belirtilmemis"),
        sirket_adi=ilan_analizi.get("sirket_adi"),
        deneyim_yili=ilan_analizi.get("deneyim_yili"),
        ham_metin=metin,
        analiz=ilan_analizi,
    )
    db.add(yeni_ilan)
    db.commit()
    db.refresh(yeni_ilan)

    return {
        "id": yeni_ilan.id,
        "analiz": ilan_analizi,
    }


@router.get("/is-ilanlari")
def is_ilanlari_listesi(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    ilanlar = (
        db.query(IsIlani)
        .order_by(IsIlani.eklenme_tarihi.desc())
        .limit(limit)
        .all()
    )

    return {
        "toplam_donen": len(ilanlar),
        "ilanlar": [
            {
                "id": i.id,
                "pozisyon_adi": i.pozisyon_adi,
                "sirket_adi": i.sirket_adi,
                "deneyim_yili": i.deneyim_yili,
                "analiz": i.analiz,
                "eklenme_tarihi": i.eklenme_tarihi.isoformat(),
            }
            for i in ilanlar
        ],
    }