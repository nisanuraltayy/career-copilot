from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, CVKaydi, IsIlani
from services.gemini_service import gemini_json_uret

router = APIRouter()


class UyumAnaliziIstegi(BaseModel):
    cv_id: int
    is_ilani_id: int


@router.post("/uyum-analizi")
def uyum_analizi(
    istek: UyumAnaliziIstegi,
    db: Session = Depends(get_db),
):
    cv = db.query(CVKaydi).filter(CVKaydi.id == istek.cv_id).first()
    if cv is None:
        return {"hata": f"CV bulunamadi (id={istek.cv_id})."}

    ilan = db.query(IsIlani).filter(IsIlani.id == istek.is_ilani_id).first()
    if ilan is None:
        return {"hata": f"Is ilani bulunamadi (id={istek.is_ilani_id})."}

    cv_beceriler_ham = cv.analiz.get("beceriler", []) if cv.analiz else []
    gerekli_beceriler_ham = ilan.analiz.get("gerekli_beceriler", []) if ilan.analiz else []
    tercih_edilen_ham = ilan.analiz.get("tercih_edilen_beceriler", []) if ilan.analiz else []

    cv_set = {b.lower().strip() for b in cv_beceriler_ham}
    gerekli_set = {b.lower().strip() for b in gerekli_beceriler_ham}
    tercih_edilen_set = {b.lower().strip() for b in tercih_edilen_ham}

    eslesen_gerekli = cv_set & gerekli_set
    eksik_gerekli = gerekli_set - cv_set
    eslesen_tercih = cv_set & tercih_edilen_set
    ekstra = cv_set - gerekli_set - tercih_edilen_set

    if len(gerekli_set) > 0:
        gerekli_uyum = len(eslesen_gerekli) / len(gerekli_set) * 100
    else:
        gerekli_uyum = 0

    if len(tercih_edilen_set) > 0:
        tercih_uyum = len(eslesen_tercih) / len(tercih_edilen_set) * 100
    else:
        tercih_uyum = 0

    v1_uyum_yuzdesi = round(gerekli_uyum * 0.7 + tercih_uyum * 0.3)

    v1_sonuc = {
        "uyum_yuzdesi": v1_uyum_yuzdesi,
        "gerekli_uyum_yuzdesi": round(gerekli_uyum),
        "tercih_uyum_yuzdesi": round(tercih_uyum),
        "eslesen_gerekli_beceriler": sorted(eslesen_gerekli),
        "eksik_gerekli_beceriler": sorted(eksik_gerekli),
        "eslesen_tercih_edilen": sorted(eslesen_tercih),
        "ekstra_beceriler": sorted(ekstra),
        "hesaplama_yontemi": "kelime_karsilastirma",
    }

    prompt = f"""Bir CV ile bir is ilani arasinda semantik uyum analizi yap.

CV BECERILERI:
{cv_beceriler_ham}

IS ILANI GEREKLI BECERILER:
{gerekli_beceriler_ham}

IS ILANI TERCIH EDILEN BECERILER:
{tercih_edilen_ham}

Gorevin:
1. Semantik eslesmeleri bul. Ornek: 'REST API' ile 'REST API tasarimi' aynidir; 'SQL' ile 'PostgreSQL' yakindir.
2. 0-100 arasi bir uyum yuzdesi ver. Sadece kelime degil anlam bazli degerlendir.
3. 2-3 cumlelik bir ozet yaz: kullanici neden bu pozisyona uyumlu/uyumsuz?

Sadece JSON dondur, baska aciklama ekleme. Su formatta:
{{
  "uyum_yuzdesi": <0-100 arasi sayi>,
  "guclu_yonler": ["...", "..."],
  "eksik_yonler": ["...", "..."],
  "ozet": "..."
}}
"""

    try:
        v2_sonuc = gemini_json_uret(prompt, model="gemini-2.5-flash")
        v2_sonuc["hesaplama_yontemi"] = "llm_semantik"
    except Exception as e:
        v2_sonuc = {
            "hata": "LLM analizi yapilamadi, sadece V1 sonucunu kullaniyoruz.",
            "teknik_detay": str(e),
        }

    return {
        "cv_id": cv.id,
        "is_ilani_id": ilan.id,
        "v1_basit": v1_sonuc,
        "v2_llm": v2_sonuc,
    }