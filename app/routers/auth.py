"""Kimlik doğrulama endpoint'leri: kayıt, giriş, token yenileme, parola, me."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import AuthError
from app.core.rate_limit import limiter
from app.core.security import refresh_token_uret, token_coz, token_uret
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    GirisIstegi,
    KayitIstegi,
    KullaniciYaniti,
    ParolaDegistirIstegi,
    TokenYaniti,
    YenilemeIstegi,
)
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_cifti(user_id: int) -> TokenYaniti:
    return TokenYaniti(
        access_token=token_uret(user_id),
        refresh_token=refresh_token_uret(user_id),
    )


@router.post("/register", response_model=TokenYaniti, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_ai)
def kayit(
    request: Request,
    istek: KayitIstegi,
    db: Session = Depends(get_db),
) -> TokenYaniti:
    user = user_service.kayit_ol(db, email=istek.email, parola=istek.parola)
    return _token_cifti(user.id)


@router.post("/login", response_model=TokenYaniti)
@limiter.limit(settings.rate_limit_ai)
def giris(
    request: Request,
    istek: GirisIstegi,
    db: Session = Depends(get_db),
) -> TokenYaniti:
    user = user_service.kimlik_dogrula(db, email=istek.email, parola=istek.parola)
    return _token_cifti(user.id)


@router.post("/refresh", response_model=TokenYaniti)
def yenile(
    istek: YenilemeIstegi,
    db: Session = Depends(get_db),
) -> TokenYaniti:
    """Geçerli refresh token ile yeni access+refresh token verir (rotasyon)."""
    user_id = token_coz(istek.refresh_token, beklenen_tip="refresh")
    if user_id is None:
        raise AuthError("Geçersiz veya süresi dolmuş refresh token.")
    user = user_service.kullanici_getir(db, user_id)
    if user is None or not user.is_active:
        raise AuthError("Kullanıcı bulunamadı veya pasif.")
    return _token_cifti(user.id)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def parola_degistir(
    istek: ParolaDegistirIstegi,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    user_service.parola_degistir(db, user, istek.eski_parola, istek.yeni_parola)


@router.get("/me", response_model=KullaniciYaniti)
def mevcut_kullanici(user: User = Depends(get_current_user)) -> User:
    return user
