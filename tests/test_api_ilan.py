"""İş ilanı endpoint'leri."""

from datetime import datetime
from types import SimpleNamespace

from app.core.exceptions import ServiceUnavailableError
from app.services import ilan_service


def _sahte_ilan(**kw):
    varsayilan = dict(
        id=1, pozisyon_adi="Backend Developer", sirket_adi="ACME",
        deneyim_yili="2-3 yil", analiz={"gerekli_beceriler": ["Python"]},
        embedding=[0.1], created_at=datetime.now(),
    )
    varsayilan.update(kw)
    return SimpleNamespace(**varsayilan)


def test_ilan_analiz_basarili(client, monkeypatch):
    monkeypatch.setattr(ilan_service, "ilan_olustur", lambda db, metin: _sahte_ilan())
    r = client.post("/is-ilani-analiz", json={"metin": "Python backend arıyoruz"})
    assert r.status_code == 201
    assert r.json()["embedding_uretildi"] is True


def test_ilan_analiz_bos_metin_reddedilir(client):
    r = client.post("/is-ilani-analiz", json={"metin": "   "})
    assert r.status_code == 422


def test_ilan_listesi(client, monkeypatch):
    monkeypatch.setattr(ilan_service, "ilan_listele", lambda db, limit: [_sahte_ilan()])
    r = client.get("/is-ilanlari")
    assert r.status_code == 200
    assert r.json()["toplam_donen"] == 1


def test_gemini_gecici_mesgulse_503(client, monkeypatch):
    """Gemini geçici olarak meşgulse (retry'lar tükenmiş) -> 503 + dostça mesaj."""
    def mesgul(db, metin):
        raise ServiceUnavailableError()

    monkeypatch.setattr(ilan_service, "ilan_olustur", mesgul)
    r = client.post("/is-ilani-analiz", json={"metin": "Python backend"})
    assert r.status_code == 503
    body = r.json()
    assert body["error"]["code"] == "service_unavailable"
    assert body["error"]["message"] == (
        "The AI service is temporarily busy. Please try again in a few seconds."
    )
    # Stack trace / iç detay sızmamalı.
    assert "teknik_detay" not in body["error"]
    assert "traceback" not in str(body).lower()
