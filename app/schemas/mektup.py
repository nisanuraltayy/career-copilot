"""Motivasyon mektubu endpoint şemaları."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MotivasyonMektubuIstegi(BaseModel):
    cv_id: int
    is_ilani_id: int


class MotivasyonMektubuYaniti(BaseModel):
    id: int
    cv_id: int
    is_ilani_id: int
    pozisyon: str
    sirket: str
    mektup_metni: str


class MektupOzet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cv_id: int
    is_ilani_id: int
    mektup_metni: str
    created_at: datetime


class MektupListesiYaniti(BaseModel):
    toplam_donen: int
    mektuplar: list[MektupOzet]
