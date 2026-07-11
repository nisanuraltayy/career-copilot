"""users tablosu + kaynaklara user_id (multi-tenancy)

Revision ID: 0002_auth
Revises: 0001_initial
Create Date: 2026-07-11

Mevcut veriyi güvenle taşır: bir "sistem" kullanıcısı oluşturur, eski kayıtları
ona bağlar, ardından user_id'yi NOT NULL yapar. Böylece production'da veri
kaybı olmadan multi-tenancy'ye geçilir.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_auth"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLOLAR = ["cv_kayitlari", "is_ilanlari", "uyum_analizleri", "motivasyon_mektuplari"]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Eski (sahipsiz) kayıtları bağlamak için devre dışı bir sistem kullanıcısı.
    # hashed_password geçerli bir bcrypt değil -> bu hesapla giriş yapılamaz.
    op.execute(
        "INSERT INTO users (email, hashed_password, is_active, created_at, updated_at) "
        "VALUES ('system@career-copilot.local', '!disabled', false, now(), now())"
    )

    for tablo in _TABLOLAR:
        op.add_column(tablo, sa.Column("user_id", sa.Integer(), nullable=True))
        op.execute(
            f"UPDATE {tablo} SET user_id = "
            "(SELECT id FROM users WHERE email='system@career-copilot.local') "
            "WHERE user_id IS NULL"
        )
        op.alter_column(tablo, "user_id", nullable=False)
        op.create_foreign_key(
            f"fk_{tablo}_user_id", tablo, "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        op.create_index(f"ix_{tablo}_user_id", tablo, ["user_id"])


def downgrade() -> None:
    for tablo in _TABLOLAR:
        op.drop_index(f"ix_{tablo}_user_id", table_name=tablo)
        op.drop_constraint(f"fk_{tablo}_user_id", tablo, type_="foreignkey")
        op.drop_column(tablo, "user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
