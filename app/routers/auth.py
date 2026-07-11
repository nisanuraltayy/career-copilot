"""Kimlik doğrulama endpoint'leri: kayıt, giriş, mevcut kullanıcı."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import token_uret
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import GirisIstegi, KayitIstegi, KullaniciYaniti, TokenYaniti
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenYaniti, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_ai)
def kayit(
    request: Request,
    istek: KayitIstegi,
    db: Session = Depends(get_db),
) -> TokenYaniti:
    user = user_service.kayit_ol(db, email=istek.email, parola=istek.parola)
    return TokenYaniti(access_token=token_uret(user.id))


@router.post("/login", response_model=TokenYaniti)
@limiter.limit(settings.rate_limit_ai)
def giris(
    request: Request,
    istek: GirisIstegi,
    db: Session = Depends(get_db),
) -> TokenYaniti:
    user = user_service.kimlik_dogrula(db, email=istek.email, parola=istek.parola)
    return TokenYaniti(access_token=token_uret(user.id))


@router.get("/me", response_model=KullaniciYaniti)
def mevcut_kullanici(user: User = Depends(get_current_user)) -> User:
    return user
