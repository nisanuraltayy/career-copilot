"""PDF metin çıkarma servisi."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import ValidationFailed


class PdfCikarimSonucu:
    def __init__(self, metin: str, sayfa_sayisi: int) -> None:
        self.metin = metin
        self.sayfa_sayisi = sayfa_sayisi


def pdf_metin_cikar(pdf_bytes: bytes) -> PdfCikarimSonucu:
    """PDF byte'larından metni çıkarır.

    Geçersiz PDF veya metin çıkarılamaması durumunda `ValidationFailed`
    fırlatır (400/422) — bunlar client hatasıdır, sunucu hatası değil.
    """
    try:
        okuyucu = PdfReader(BytesIO(pdf_bytes))
    except (PdfReadError, Exception) as hata:  # bozuk/geçersiz dosya
        raise ValidationFailed("Geçerli bir PDF yükleyin.") from hata

    parcalar = []
    for sayfa in okuyucu.pages:
        parcalar.append(sayfa.extract_text() or "")
    metin = "\n".join(parcalar)

    if not metin.strip():
        raise ValidationFailed(
            "PDF'ten metin çıkarılamadı. Taranmış (görüntü) bir PDF olabilir."
        )

    return PdfCikarimSonucu(metin=metin, sayfa_sayisi=len(okuyucu.pages))
