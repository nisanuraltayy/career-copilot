"""CV endpoint şemaları."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CVAnaliz(BaseModel):
    """Gemini'nin CV'den çıkardığı yapılandırılmış analiz."""

    beceriler: list[str] = []
    deneyimler: list[str] = []
    egitim: str | None = None

    model_config = ConfigDict(extra="allow")


class CVYuklemeYaniti(BaseModel):
    id: int
    dosya_adi: str
    sayfa_sayisi: int
    karakter_sayisi: int
    analiz: dict
    embedding_uretildi: bool


class CVOzet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dosya_adi: str
    karakter_sayisi: int
    sayfa_sayisi: int
    analiz: dict
    created_at: datetime


class CVListesiYaniti(BaseModel):
    toplam_donen: int
    kayitlar: list[CVOzet]
