"""initial schema (cv, ilan, uyum, mektup) + pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-10

Not: 3072 boyutlu embedding kolonlarında ivfflat/hnsw ANN index KURULMAZ
(pgvector index limiti 2000 boyut). Bu boyutta arama exact scan yapar; küçük/
orta veri için yeterlidir. Ölçek gerekirse embedding_dim 1536'ya düşürülüp
buraya bir hnsw index migration'ı eklenebilir.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 3072


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "cv_kayitlari",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dosya_adi", sa.String(length=255), nullable=False),
        sa.Column("karakter_sayisi", sa.Integer(), nullable=False),
        sa.Column("sayfa_sayisi", sa.Integer(), nullable=False),
        sa.Column("analiz", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cv_kayitlari_created_at", "cv_kayitlari", ["created_at"])

    op.create_table(
        "is_ilanlari",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pozisyon_adi", sa.String(length=255), nullable=False),
        sa.Column("sirket_adi", sa.String(length=255), nullable=True),
        sa.Column("deneyim_yili", sa.String(length=100), nullable=True),
        sa.Column("ham_metin", sa.Text(), nullable=False),
        sa.Column("analiz", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_is_ilanlari_created_at", "is_ilanlari", ["created_at"])

    op.create_table(
        "uyum_analizleri",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cv_id", sa.Integer(), sa.ForeignKey("cv_kayitlari.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_ilani_id", sa.Integer(), sa.ForeignKey("is_ilanlari.id", ondelete="CASCADE"), nullable=False),
        sa.Column("v1_sonuc", postgresql.JSONB(), nullable=False),
        sa.Column("v2_sonuc", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_uyum_analizleri_cv_id", "uyum_analizleri", ["cv_id"])
    op.create_index("ix_uyum_analizleri_is_ilani_id", "uyum_analizleri", ["is_ilani_id"])

    op.create_table(
        "motivasyon_mektuplari",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cv_id", sa.Integer(), sa.ForeignKey("cv_kayitlari.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_ilani_id", sa.Integer(), sa.ForeignKey("is_ilanlari.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mektup_metni", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_motivasyon_mektuplari_cv_id", "motivasyon_mektuplari", ["cv_id"])
    op.create_index("ix_motivasyon_mektuplari_is_ilani_id", "motivasyon_mektuplari", ["is_ilani_id"])


def downgrade() -> None:
    op.drop_table("motivasyon_mektuplari")
    op.drop_table("uyum_analizleri")
    op.drop_table("is_ilanlari")
    op.drop_table("cv_kayitlari")
