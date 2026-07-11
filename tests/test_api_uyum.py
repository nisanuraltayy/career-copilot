"""Uyum analizi endpoint'leri — hata soyutlaması dahil."""

from types import SimpleNamespace

from app.core.exceptions import ResourceNotFound
from app.services import uyum_service


def test_uyum_analizi_basarili(client, monkeypatch):
    def sahte(db, user_id, cv_id, is_ilani_id):
        return SimpleNamespace(
            id=10, cv_id=cv_id, is_ilani_id=is_ilani_id,
            v1_sonuc={"uyum_yuzdesi": 70}, v2_sonuc={"uyum_yuzdesi": 80},
        )

    monkeypatch.setattr(uyum_service, "uyum_analizi_yap", sahte)
    r = client.post("/uyum-analizi", json={"cv_id": 1, "is_ilani_id": 2})
    assert r.status_code == 201
    assert r.json()["v1_basit"]["uyum_yuzdesi"] == 70


def test_uyum_analizi_cv_yok_404(client, monkeypatch):
    def patla(db, user_id, cv_id, is_ilani_id):
        raise ResourceNotFound("CV bulunamadı (id=99).")

    monkeypatch.setattr(uyum_service, "uyum_analizi_yap", patla)
    r = client.post("/uyum-analizi", json={"cv_id": 99, "is_ilani_id": 2})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
