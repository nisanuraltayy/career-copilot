"""CV endpoint'leri — service katmanı mocklanır, DB'ye vurulmaz."""

from pathlib import Path
from types import SimpleNamespace

from app.services import cv_service

FIXTURE = Path(__file__).parent / "fixtures" / "ornek_cv.pdf"


def _sahte_cv(**kw):
    varsayilan = dict(
        id=1, dosya_adi="ornek_cv.pdf", sayfa_sayisi=1, karakter_sayisi=120,
        analiz={"beceriler": ["Python"]}, embedding=[0.1],
    )
    varsayilan.update(kw)
    return SimpleNamespace(**varsayilan)


def test_cv_yukle_basarili(client, monkeypatch):
    monkeypatch.setattr(cv_service, "cv_olustur", lambda db, dosya_adi, pdf_bytes: _sahte_cv())
    r = client.post(
        "/cv-yukle",
        files={"dosya": ("ornek_cv.pdf", FIXTURE.read_bytes(), "application/pdf")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1
    assert body["embedding_uretildi"] is True


def test_cv_yukle_pdf_disi_reddedilir(client):
    r = client.post(
        "/cv-yukle",
        files={"dosya": ("kotu.txt", b"merhaba", "text/plain")},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_failed"


def test_cv_gecmis(client, monkeypatch):
    monkeypatch.setattr(cv_service, "cv_listele", lambda db, limit: [
        _sahte_cv(id=2, created_at=__import__("datetime").datetime.now())
    ])
    r = client.get("/cv-gecmis?limit=5")
    assert r.status_code == 200
    assert r.json()["toplam_donen"] == 1


def test_cv_gecmis_limit_dogrulama(client):
    r = client.get("/cv-gecmis?limit=0")
    assert r.status_code == 422
