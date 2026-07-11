"""Ortak FastAPI bağımlılıkları (dependencies)."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.core.security import token_coz
from app.db.models import User
from app.db.session import get_db
from app.services import user_service

# auto_error=False: başlık yoksa None döner, biz kendi hata formatımızla
# (AuthError -> 401 { error: {...} }) yanıt veririz. tokenUrl sadece Swagger
# "Authorize" düğmesi içindir.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Bearer token'dan aktif kullanıcıyı çözer; geçersizse 401."""
    if not token:
        raise AuthError("Kimlik doğrulaması gerekli.")
    user_id = token_coz(token)
    if user_id is None:
        raise AuthError("Geçersiz veya süresi dolmuş token.")
    user = user_service.kullanici_getir(db, user_id)
    if user is None or not user.is_active:
        raise AuthError("Kullanıcı bulunamadı veya pasif.")
    return user
