"""Veritabanı engine ve session yönetimi."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Render/Heroku gibi platformlar DATABASE_URL'i "postgres://" ile verir;
# SQLAlchemy 2.0 "postgresql://" bekler. Deploy'da kırılmaması için normalize et.
_db_url = str(settings.database_url)
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    _db_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=settings.db_pool_pre_ping,  # bağlantı kopmalarına dayanıklılık
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: request başına bir session açar, sonunda kapatır."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
