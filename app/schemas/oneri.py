"""İş önerisi endpoint şemaları."""

from pydantic import BaseModel


class OneriOgesi(BaseModel):
    ilan_id: int
    pozisyon_adi: str
    sirket_adi: str | None
    deneyim_yili: str | None
    uyum_skoru: float
    uzaklik: float


class OneriYaniti(BaseModel):
    cv_id: int
    cv_dosya_adi: str
    toplam_oneri: int
    oneriler: list[OneriOgesi]
