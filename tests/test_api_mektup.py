"""Motivasyon mektubu endpoint'leri."""

from types import SimpleNamespace

from app.core.exceptions import ResourceNotFound
from app.services import mektup_service


def test_mektup_uret_basarili(client, monkeypatch):
    def sahte(db, user_id, cv_id, is_ilani_id):
        ilan = SimpleNamespace(pozisyon_adi="Backend Dev", sirket_adi="ACME")
        return SimpleNamespace(
            id=7, cv_id=cv_id, is_ilani_id=is_ilani_id,
            mektup_metni="Sayin Yetkili, ...", ilan=ilan,
        )

    monkeypatch.setattr(mektup_service, "mektup_uret", sahte)
    r = client.post("/motivasyon-mektubu", json={"cv_id": 1, "is_ilani_id": 2})
    assert r.status_code == 201
    assert r.json()["sirket"] == "ACME"
    assert "Sayin" in r.json()["mektup_metni"]


def test_mektup_uret_ilan_yok_404(client, monkeypatch):
    def patla(db, user_id, cv_id, is_ilani_id):
        raise ResourceNotFound("İş ilanı bulunamadı.")

    monkeypatch.setattr(mektup_service, "mektup_uret", patla)
    r = client.post("/motivasyon-mektubu", json={"cv_id": 1, "is_ilani_id": 99})
    assert r.status_code == 404
