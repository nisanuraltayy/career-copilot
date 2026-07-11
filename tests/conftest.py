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
# Testlerde rate limiting kapalı: aynı IP'den çok sayıda istek 429'a takılmasın.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")

from types import SimpleNamespace  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.deps import get_current_user  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402

# Testlerde varsayılan olarak kimliği doğrulanmış sahte kullanıcı.
TEST_USER = SimpleNamespace(id=1, email="test@example.com", is_active=True)


@pytest.fixture
def fake_db() -> MagicMock:
    """Metotları çağrılabilir sahte bir SQLAlchemy Session."""
    return MagicMock(name="Session")


@pytest.fixture
def client(fake_db: MagicMock) -> TestClient:
    """Kimliği doğrulanmış istemci: get_current_user sahte kullanıcıya ezilir.
    Böylece endpoint testleri token yönetmeden çalışır."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(fake_db: MagicMock) -> TestClient:
    """Kimliksiz istemci: get_current_user EZİLMEZ — auth zorunluluğunu test eder."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
