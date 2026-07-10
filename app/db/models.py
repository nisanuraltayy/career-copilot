"""SQLAlchemy ORM modelleri.

Senior notları:
- `cv_id` / `is_ilani_id` artık gerçek ForeignKey — referans bütünlüğü DB'de
  garanti altında, ilişkiler ORM üzerinden gezilebilir.
- `embedding` kolonu nullable: embedding üretimi başarısız olsa da kayıt
  saklanabilir (graceful degradation).
- Zaman kolonları timezone-aware ve indexli (sıralama sorguları için).
"""


from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON as SA_JSON
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin

# Postgres'te JSONB (indekslenebilir, ikili saklama); diğer motorlarda (test
# amaçlı SQLite) düz JSON'a düşer.
JsonType = SA_JSON().with_variant(JSONB(), "postgresql")


class CVKaydi(Base, TimestampMixin):
    __tablename__ = "cv_kayitlari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dosya_adi: Mapped[str] = mapped_column(String(255), nullable=False)
    karakter_sayisi: Mapped[int] = mapped_column(Integer, nullable=False)
    sayfa_sayisi: Mapped[int] = mapped_column(Integer, nullable=False)
    analiz: Mapped[dict] = mapped_column(JsonType, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )

    uyum_analizleri: Mapped[list["UyumAnalizi"]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )
    mektuplar: Mapped[list["MotivasyonMektubu"]] = relationship(
        back_populates="cv", cascade="all, delete-orphan"
    )


class IsIlani(Base, TimestampMixin):
    __tablename__ = "is_ilanlari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pozisyon_adi: Mapped[str] = mapped_column(String(255), nullable=False)
    sirket_adi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deneyim_yili: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ham_metin: Mapped[str] = mapped_column(Text, nullable=False)
    analiz: Mapped[dict] = mapped_column(JsonType, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )

    uyum_analizleri: Mapped[list["UyumAnalizi"]] = relationship(
        back_populates="ilan", cascade="all, delete-orphan"
    )
    mektuplar: Mapped[list["MotivasyonMektubu"]] = relationship(
        back_populates="ilan", cascade="all, delete-orphan"
    )


class UyumAnalizi(Base, TimestampMixin):
    __tablename__ = "uyum_analizleri"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_id: Mapped[int] = mapped_column(
        ForeignKey("cv_kayitlari.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_ilani_id: Mapped[int] = mapped_column(
        ForeignKey("is_ilanlari.id", ondelete="CASCADE"), nullable=False, index=True
    )
    v1_sonuc: Mapped[dict] = mapped_column(JsonType, nullable=False)
    v2_sonuc: Mapped[dict] = mapped_column(JsonType, nullable=False)

    cv: Mapped["CVKaydi"] = relationship(back_populates="uyum_analizleri")
    ilan: Mapped["IsIlani"] = relationship(back_populates="uyum_analizleri")


class MotivasyonMektubu(Base, TimestampMixin):
    __tablename__ = "motivasyon_mektuplari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_id: Mapped[int] = mapped_column(
        ForeignKey("cv_kayitlari.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_ilani_id: Mapped[int] = mapped_column(
        ForeignKey("is_ilanlari.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mektup_metni: Mapped[str] = mapped_column(Text, nullable=False)

    cv: Mapped["CVKaydi"] = relationship(back_populates="mektuplar")
    ilan: Mapped["IsIlani"] = relationship(back_populates="mektuplar")
