from fastapi import APIRouter, UploadFile, File, Depends
from pypdf import PdfReader
from io import BytesIO
from sqlalchemy.orm import Session

from database import get_db, CVKaydi
from services.gemini_service import gemini_json_uret, gemini_embedding_uret

router = APIRouter()


def _cv_analizden_metin(analiz: dict) -> str:
    """CV analiz JSON'unu embedding icin temiz, duz metne cevirir.
    JSON sozdizimi degil, sadece anlam tasiyan icerik gonderilir.
    analiz beklenmedik format donerse bile cokmez (defensive)."""
    parcalar = []

    beceriler = analiz.get("beceriler")
    if isinstance(beceriler, list) and beceriler:
        parcalar.append("Beceriler: " + ", ".join(str(b) for b in beceriler))

    deneyimler = analiz.get("deneyimler")
    if isinstance(deneyimler, list) and deneyimler:
        parcalar.append("Deneyimler: " + ", ".join(str(d) for d in deneyimler))

    egitim = analiz.get("egitim")
    if egitim:
        parcalar.append("Egitim: " + str(egitim))

    return ". ".join(parcalar)


@router.post("/cv-yukle")
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
        cv_analizi = gemini_json_uret(prompt)
    except Exception as e:
        return {
            "hata": "CV analizi yapilamadi.",
            "teknik_detay": str(e),
        }

    # Analiz JSON'undan temiz metin kur, embedding uret (basarisizsa None doner)
    embed_metni = _cv_analizden_metin(cv_analizi)
    embedding = gemini_embedding_uret(embed_metni) if embed_metni else None

    yeni_kayit = CVKaydi(
        dosya_adi=dosya.filename,
        karakter_sayisi=len(metin),
        sayfa_sayisi=len(pdf_okuyucu.pages),
        analiz=cv_analizi,
        embedding=embedding,
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
        "embedding_uretildi": embedding is not None,
    }


@router.get("/cv-gecmis")
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