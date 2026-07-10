"""SQLAlchemy declarative base.

Modeller `Base`'i buradan alır; Alembic de metadata'yı buradan okur
(tek doğruluk kaynağı).
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC şimdi. `datetime.utcnow` (deprecated, naive) yerine."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Tüm modellerin ortak tabanı."""


class TimestampMixin:
    """created_at / updated_at kolonlarını ekleyen mixin.

    Zaman DB tarafında (`func.now()`) da atanır; böylece toplu insert veya
    farklı zaman dilimli uygulama sunucuları tutarlı kalır.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        onupdate=utcnow,
    )
