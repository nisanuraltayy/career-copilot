"""Ortak test fixture'ları.

Testler gerçek veritabanına veya Gemini API'sine ASLA vurmaz:
- Ortam değişkenleri burada sahte değerlerle set edilir (CI'da .env yok).
- `get_db` bağımlılığı sahte bir Session ile ezilir.
- Service katmanı fonksiyonları test bazında monkeypatch'lenir.
"""

import os

# app import edilmeden ÖNCE zorunlu ayarları enjekte et (fail-fast config'i
# tatmin etmek için). Gerçek bir bağlantı kurulmaz.
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test:test@localhost:5432/testdb"
)
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-used")
os.environ.setdefault("ENVIRONMENT", "test")

from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def fake_db() -> MagicMock:
    """Metotları çağrılabilir sahte bir SQLAlchemy Session."""
    return MagicMock(name="Session")


@pytest.fixture
def client(fake_db: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
