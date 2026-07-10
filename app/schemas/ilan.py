"""İş ilanı endpoint şemaları."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IsIlaniIstegi(BaseModel):
    metin: str = Field(..., min_length=1, description="İş ilanı ham metni")

    @field_validator("metin")
    @classmethod
    def _bos_olamaz(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("İş ilanı metni boş olamaz.")
        return v


class IsIlaniAnalizYaniti(BaseModel):
    id: int
    analiz: dict
    embedding_uretildi: bool


class IsIlaniOzet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pozisyon_adi: str
    sirket_adi: str | None
    deneyim_yili: str | None
    analiz: dict
    created_at: datetime


class IsIlaniListesiYaniti(BaseModel):
    toplam_donen: int
    ilanlar: list[IsIlaniOzet]
