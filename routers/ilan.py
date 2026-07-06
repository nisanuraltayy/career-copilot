from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, IsIlani
from services.gemini_service import gemini_json_uret, gemini_embedding_uret

router = APIRouter()


class IsIlaniIstegi(BaseModel):
    metin: str


def _ilan_analizden_metin(analiz: dict) -> str:
    """Ilan analiz JSON'unu embedding icin temiz, duz metne cevirir."""
    parcalar = []

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

    # Analiz JSON'undan temiz metin kur, embedding uret (basarisizsa None doner)
    embed_metni = _ilan_analizden_metin(ilan_analizi)
    embedding = gemini_embedding_uret(embed_metni) if embed_metni else None

    yeni_ilan = IsIlani(
        pozisyon_adi=ilan_analizi.get("pozisyon_adi", "Belirtilmemis"),
        sirket_adi=ilan_analizi.get("sirket_adi"),
        deneyim_yili=ilan_analizi.get("deneyim_yili"),
        ham_metin=metin,
        analiz=ilan_analizi,
        embedding=embedding,
    )
    db.add(yeni_ilan)
    db.commit()
    db.refresh(yeni_ilan)

    return {
        "id": yeni_ilan.id,
        "analiz": ilan_analizi,
        "embedding_uretildi": embedding is not None,
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