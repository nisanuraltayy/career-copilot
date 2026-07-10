"""Yapılandırma (Settings) davranışı."""

from app.core.config import Settings

_ZORUNLU = {
    "DATABASE_URL": "postgresql://u:p@localhost:5432/d",
    "GEMINI_API_KEY": "k",
}


def test_cors_virgulle_ayrilir(monkeypatch):
    for k, v in _ZORUNLU.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com")
    s = Settings()
    assert s.cors_origins == ["http://a.com", "http://b.com"]


def test_cors_varsayilan(monkeypatch):
    for k, v in _ZORUNLU.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    s = Settings()
    assert "http://localhost:5173" in s.cors_origins


def test_is_production_bayragi(monkeypatch):
    for k, v in _ZORUNLU.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert Settings().is_production is True
