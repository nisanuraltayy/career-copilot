"""Kimlik güvenliği yardımcıları: parola hash'leme (bcrypt) ve JWT.

Parolalar asla düz saklanmaz; bcrypt (adaptif, salt'lı) ile hash'lenir.
Token'lar HS256 imzalı JWT'dir; `sub` claim'i kullanıcı id'sini taşır.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings


def hash_parola(parola: str) -> str:
    """Parolayı bcrypt ile hash'ler (utf-8 string döner)."""
    return bcrypt.hashpw(parola.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def parola_dogrula(parola: str, hashli: str) -> bool:
    """Düz parolayı hash ile karşılaştırır (sabit zamanlı)."""
    try:
        return bcrypt.checkpw(parola.encode("utf-8"), hashli.encode("utf-8"))
    except ValueError:
        # Bozuk/uyumsuz hash -> doğrulama başarısız.
        return False


def token_uret(kullanici_id: int) -> str:
    """Kullanıcı için imzalı bir JWT erişim token'ı üretir."""
    simdi = datetime.now(UTC)
    payload = {
        "sub": str(kullanici_id),
        "iat": simdi,
        "exp": simdi + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def token_coz(token: str) -> int | None:
    """Token'ı doğrular ve kullanıcı id'sini döndürür; geçersizse None."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
