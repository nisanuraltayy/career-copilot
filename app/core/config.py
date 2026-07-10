"""Uygulama yapılandırması.

Tüm ayarlar tek bir yerden, tip güvenli şekilde yönetilir (12-factor).
Ortam değişkenleri `.env` dosyasından veya gerçek env'den okunur.
Eksik/hatalı config uygulama açılışında (fail-fast) hata verir; runtime'da
sessizce None dönmez.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Uygulama ---
    app_name: str = "Career Copilot"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    # JSON formatında log üret (production/log-aggregation için). Development'ta
    # okunabilir düz metin tercih edilir.
    log_json: bool = False

    # --- Veritabanı ---
    database_url: PostgresDsn = Field(
        ...,
        description="postgresql://user:pass@host:5432/db",
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True

    # --- CORS ---
    # Virgülle ayrılmış origin listesi, örn:
    # CORS_ORIGINS=http://localhost:5173,https://app.example.com
    # NoDecode: pydantic-settings ham string'i JSON olarak çözmeye çalışmasın,
    # aşağıdaki validator virgülle ayırsın.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- Gemini / AI ---
    gemini_api_key: str = Field(..., description="Google Gemini API anahtarı")
    gemini_json_model: str = "gemini-flash-latest"
    gemini_text_model: str = "gemini-flash-latest"
    gemini_semantic_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    # gemini-embedding-001 3072 boyut üretir. Not: pgvector'ün ivfflat/hnsw
    # index'leri en fazla 2000 boyut destekler; 3072 boyutta ANN index kurulamaz
    # (sadece exact scan). Ölçek gerektiğinde 1536'ya düşürülüp index eklenebilir.
    embedding_dim: int = 3072

    # --- Gemini yeniden deneme (retry) politikası ---
    # Google, yoğun trafikte geçici olarak 503 UNAVAILABLE / 429 döndürebilir.
    # Bu geçici hatalar üstel geri çekilme (exponential backoff) ile yeniden
    # denenir. max_retries=4 -> toplam 5 deneme.
    gemini_max_retries: int = 4
    gemini_retry_base_delay: float = 0.5  # saniye; gecikme = base * 2**deneme
    gemini_retry_max_delay: float = 8.0  # tek bir beklemenin tavanı (saniye)

    # --- Dosya yükleme limitleri ---
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        """CORS_ORIGINS env'i virgülle ayrılmış string olarak da kabul et."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Ayarları tekil (singleton) olarak döndür. FastAPI Depends ile de
    kullanılabilir; test'te `get_settings.cache_clear()` ile sıfırlanır."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
