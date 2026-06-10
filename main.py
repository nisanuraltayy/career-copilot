from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Depends
from pypdf import PdfReader
from io import BytesIO
from google import genai
from dotenv import load_dotenv
import os
import json
from sqlalchemy.orm import Session
from database import get_db, CVKaydi, IsIlani


load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class IsIlaniIstegi(BaseModel):
    metin: str


class UyumAnaliziIstegi(BaseModel):
    cv_id: int
    is_ilani_id: int


app = FastAPI(title="Career Copilot", version="0.1.0")


@app.get("/")
def ana_sayfa():
    return {"mesaj": "Career Copilot calisiyor!"}


@app.get("/saglik")
def saglik_kontrolu():
    return {"durum": "iyi"}


@app.post("/cv-yukle")
def cv_yukle(
    dosya: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    pdf_bytes = dosya.file.read()
    try:
        pdf_okuyucu = PdfReader(BytesIO(pdf_bytes))
    except Exception:
        return {"hata": "Gecerli bir PDF yukleyin."}

    metin = ""
    for sayfa in pdf_okuyucu.pages:
        metin += sayfa.extract_text() + "\n"

    if not metin.strip():
        return {"hata": "PDF'ten metin cikarilamadi. Taranmis bir PDF olabilir."}

    prompt = f"""Asagida bir ozgecmis (CV) metni var. Bu CV'den asagidaki bilgileri JSON formatinda cikar:
- beceriler (liste): teknik beceriler, diller, frameworkler, araclar
- deneyimler (liste): pozisyon ve sirket isimleri
- egitim (string): en yuksek egitim seviyesi ve alani

Sadece JSON dondur, baska aciklama ekleme.

CV METNI:
{metin}
"""

    try:
        yanit = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
    except Exception as e:
        return {
            "hata": "AI servisi su an yanit veremiyor. Lutfen birkac dakika sonra tekrar deneyin.",
            "teknik_detay": str(e),
        }

    cevap_metni = yanit.text.strip()
    if cevap_metni.startswith("```json"):
        cevap_metni = cevap_metni.removeprefix("```json").removesuffix("```").strip()
    elif cevap_metni.startswith("```"):
        cevap_metni = cevap_metni.removeprefix("```").removesuffix("```").strip()

    try:
        cv_analizi = json.loads(cevap_metni)
    except json.JSONDecodeError:
        return {
            "hata": "LLM cevabi JSON olarak parse edilemedi.",
            "ham_cevap": cevap_metni,
        }

    yeni_kayit = CVKaydi(
        dosya_adi=dosya.filename,
        karakter_sayisi=len(metin),
        sayfa_sayisi=len(pdf_okuyucu.pages),
        analiz=cv_analizi,
    )
    db.add(yeni_kayit)
    db.commit()
    db.refresh(yeni_kayit)

    return {
        "id": yeni_kayit.id,
        "dosya_adi": dosya.filename,
        "sayfa_sayisi": len(pdf_okuyucu.pages),
        "karakter_sayisi": len(metin),
        "analiz": cv_analizi,
    }


@app.get("/cv-gecmis")
def cv_gecmis(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    kayitlar = (
        db.query(CVKaydi)
        .order_by(CVKaydi.yukleme_tarihi.desc())
        .limit(limit)
        .all()
    )

    return {
        "toplam_donen": len(kayitlar),
        "kayitlar": [
            {
                "id": k.id,
                "dosya_adi": k.dosya_adi,
                "karakter_sayisi": k.karakter_sayisi,
                "sayfa_sayisi": k.sayfa_sayisi,
                "analiz": k.analiz,
                "yukleme_tarihi": k.yukleme_tarihi.isoformat(),
            }
            for k in kayitlar
        ],
    }


@app.post("/is-ilani-analiz")
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
        yanit = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
    except Exception as e:
        return {
            "hata": "AI servisi su an yanit veremiyor. Lutfen birkac dakika sonra tekrar deneyin.",
            "teknik_detay": str(e),
        }

    cevap_metni = yanit.text.strip()
    if cevap_metni.startswith("```json"):
        cevap_metni = cevap_metni.removeprefix("```json").removesuffix("```").strip()
    elif cevap_metni.startswith("```"):
        cevap_metni = cevap_metni.removeprefix("```").removesuffix("```").strip()

    try:
        ilan_analizi = json.loads(cevap_metni)
    except json.JSONDecodeError:
        return {
            "hata": "LLM cevabi JSON olarak parse edilemedi.",
            "ham_cevap": cevap_metni,
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


@app.get("/is-ilanlari")
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


@app.post("/uyum-analizi")
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
        yanit = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        cevap_metni = yanit.text.strip()
        if cevap_metni.startswith("```json"):
            cevap_metni = cevap_metni.removeprefix("```json").removesuffix("```").strip()
        elif cevap_metni.startswith("```"):
            cevap_metni = cevap_metni.removeprefix("```").removesuffix("```").strip()
        v2_sonuc = json.loads(cevap_metni)
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