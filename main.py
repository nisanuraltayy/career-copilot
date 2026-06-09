from fastapi import FastAPI, UploadFile, File
from pypdf import PdfReader
from io import BytesIO
from google import genai
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Career Copilot", version="0.1.0")


@app.get("/")
def ana_sayfa():
    return {"mesaj": "Career Copilot calisiyor!"}


@app.get("/saglik")
def saglik_kontrolu():
    return {"durum": "iyi"}


@app.post("/cv-yukle")
def cv_yukle(dosya: UploadFile = File(...)):
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

    return {
        "dosya_adi": dosya.filename,
        "sayfa_sayisi": len(pdf_okuyucu.pages),
        "karakter_sayisi": len(metin),
        "analiz": cv_analizi,
    }