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


def token_uret(
    kullanici_id: int, tip: str = "access", sure_dk: int | None = None
) -> str:
    """Kullanıcı için imzalı bir JWT üretir.

    tip: "access" (kısa ömürlü, API çağrıları) veya "refresh" (uzun ömürlü,
    yeni access token almak için). `type` claim'i ile ayrılır ki bir refresh
    token API erişimi için kullanılamasın.
    """
    if sure_dk is None:
        sure_dk = settings.jwt_expire_minutes
    simdi = datetime.now(UTC)
    payload = {
        "sub": str(kullanici_id),
        "type": tip,
        "iat": simdi,
        "exp": simdi + timedelta(minutes=sure_dk),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def refresh_token_uret(kullanici_id: int) -> str:
    """Uzun ömürlü refresh token üretir."""
    return token_uret(
        kullanici_id, tip="refresh", sure_dk=settings.jwt_refresh_expire_minutes
    )


def token_coz(token: str, beklenen_tip: str = "access") -> int | None:
    """Token'ı doğrular, tipini kontrol eder ve kullanıcı id'sini döndürür.

    Geçersiz/süresi dolmuş veya tip uyuşmuyorsa None (örn. refresh token,
    access beklenen yerde kabul edilmez).
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != beklenen_tip:
            return None
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
