"""Uyum analizi endpoint şemaları."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UyumAnaliziIstegi(BaseModel):
    cv_id: int
    is_ilani_id: int


class V1Sonuc(BaseModel):
    """Deterministik kelime eşleştirme sonucu."""

    uyum_yuzdesi: int
    gerekli_uyum_yuzdesi: int
    tercih_uyum_yuzdesi: int
    eslesen_gerekli_beceriler: list[str]
    eksik_gerekli_beceriler: list[str]
    eslesen_tercih_edilen: list[str]
    ekstra_beceriler: list[str]
    hesaplama_yontemi: str = "kelime_karsilastirma"


class UyumAnaliziYaniti(BaseModel):
    id: int
    cv_id: int
    is_ilani_id: int
    v1_basit: dict
    v2_llm: dict


class UyumAnaliziOzet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cv_id: int
    is_ilani_id: int
    v1_sonuc: dict
    v2_sonuc: dict
    created_at: datetime


class UyumAnaliziListesiYaniti(BaseModel):
    toplam_donen: int
    analizler: list[UyumAnaliziOzet]
