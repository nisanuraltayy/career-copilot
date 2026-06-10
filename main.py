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