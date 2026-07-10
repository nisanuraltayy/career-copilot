"""İş önerisi endpoint'i — hata durumları dahil."""

from types import SimpleNamespace

from app.core.exceptions import BusinessRuleError, ResourceNotFound
from app.services import oneri_service


def test_oneriler_basarili(client, monkeypatch):
    cv = SimpleNamespace(id=1, dosya_adi="cv.pdf")
    oneriler = [
        {"ilan_id": 5, "pozisyon_adi": "Backend Dev", "sirket_adi": "ACME",
         "deneyim_yili": "2 yil", "uyum_skoru": 88.5, "uzaklik": 0.115},
    ]
    monkeypatch.setattr(oneri_service, "is_onerileri", lambda db, cv_id, limit: (cv, oneriler))
    r = client.get("/is-onerileri/1")
    assert r.status_code == 200
    assert r.json()["toplam_oneri"] == 1
    assert r.json()["oneriler"][0]["uyum_skoru"] == 88.5


def test_oneriler_cv_yok_404(client, monkeypatch):
    def patla(db, cv_id, limit):
        raise ResourceNotFound(f"CV bulunamadı (id={cv_id}).")

    monkeypatch.setattr(oneri_service, "is_onerileri", patla)
    r = client.get("/is-onerileri/99")
    assert r.status_code == 404


def test_oneriler_embedding_yok_400(client, monkeypatch):
    def patla(db, cv_id, limit):
        raise BusinessRuleError("Bu CV'nin embedding'i yok.")

    monkeypatch.setattr(oneri_service, "is_onerileri", patla)
    r = client.get("/is-onerileri/1")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "business_rule"


def test_oneriler_gecersiz_cv_id_422(client):
    r = client.get("/is-onerileri/0")  # ge=1 ihlali
    assert r.status_code == 422
