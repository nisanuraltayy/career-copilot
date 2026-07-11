"""Kullanıcı iş mantığı: kayıt ve kimlik doğrulama."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, BusinessRuleError, ConflictError
from app.core.logging import get_logger
from app.core.security import hash_parola, parola_dogrula
from app.db.models import User

logger = get_logger(__name__)


def email_ile_getir(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def kullanici_getir(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def kayit_ol(db: Session, email: str, parola: str) -> User:
    if email_ile_getir(db, email) is not None:
        raise ConflictError("Bu e-posta zaten kayıtlı.")
    user = User(email=email, hashed_password=hash_parola(parola), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user_registered", extra={"user_id": user.id})
    return user


def kimlik_dogrula(db: Session, email: str, parola: str) -> User:
    user = email_ile_getir(db, email)
    # Kullanıcı yoksa da parola doğrulaması yaparız (timing) — ama basit tutuyoruz.
    if user is None or not parola_dogrula(parola, user.hashed_password):
        raise AuthError("E-posta veya parola hatalı.")
    if not user.is_active:
        raise AuthError("Hesap pasif.")
    return user


def parola_degistir(db: Session, user: User, eski: str, yeni: str) -> None:
    """Giriş yapmış kullanıcının parolasını değiştirir (eski parola doğrulanır)."""
    if not parola_dogrula(eski, user.hashed_password):
        raise AuthError("Mevcut parola hatalı.")
    if eski == yeni:
        raise BusinessRuleError("Yeni parola eskisiyle aynı olamaz.")
    user.hashed_password = hash_parola(yeni)
    db.add(user)
    db.commit()
    logger.info("password_changed", extra={"user_id": user.id})
