"""Gemini (Google GenAI) istemci sarmalayıcısı.

Tüm dış AI çağrıları burada toplanır. Katman dışarıya sadece anlamlı
uygulama hataları fırlatır; SDK'ya özgü istisnalar sızmaz. Böylece
router/service katmanı sağlayıcıdan bağımsız kalır (yarın OpenAI'a geçilse
sadece bu dosya değişir).

Dayanıklılık: Google yoğun trafikte geçici olarak `503 UNAVAILABLE` veya
`429` döndürebilir. Bu GEÇİCİ hatalar üstel geri çekilme (exponential backoff
+ jitter) ile birkaç kez yeniden denenir. Denemeler tükenirse
`ServiceUnavailableError` (HTTP 503) fırlatılır; kalıcı/beklenmedik hatalarda
ise `UpstreamServiceError` (HTTP 502). Her iki durumda da ham hata/stack trace
istemciye sızmaz — yalnızca sunucu logunda kalır.

İstemci lazy (ilk kullanımda) oluşturulur — böylece test ortamı gerçek API
anahtarı olmadan da import edilebilir.
"""

import json
import random
import time
from collections.abc import Callable
from functools import lru_cache
from typing import TypeVar

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError, UpstreamServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Yeniden denenmeye değer geçici HTTP durum kodları:
# 429 (rate limit), 500/502/503/504 (sunucu tarafı geçici hatalar).
_GECICI_KODLAR = frozenset({429, 500, 502, 503, 504})


@lru_cache
def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _gecici_mi(hata: Exception) -> bool:
    """Hata yeniden denenebilir (geçici) mi?

    - SDK'nın HTTP hatalarında `.code` (durum kodu) alanı bulunur.
    - `ServerError` (tüm 5xx) her zaman geçicidir.
    - Ağ seviyesi hatalar (timeout, bağlantı kopması) geçicidir.
    """
    kod = getattr(hata, "code", None)
    if isinstance(kod, int) and kod in _GECICI_KODLAR:
        return True
    if isinstance(hata, genai_errors.ServerError):
        return True
    return isinstance(hata, httpx.TimeoutException | httpx.TransportError)


def _backoff_suresi(deneme: int) -> float:
    """Üstel geri çekilme + tam jitter (thundering herd'i önler).

    deneme 0,1,2,3 -> tavan 0.5,1,2,4 sn (max_delay ile sınırlı); gerçek
    bekleme [0, tavan] arasında rastgele.
    """
    tavan = min(
        settings.gemini_retry_max_delay,
        settings.gemini_retry_base_delay * (2**deneme),
    )
    return random.uniform(0, tavan)


def _retry_ile_cagir(fn: Callable[[], T], islem: str) -> T:
    """`fn`'i geçici hatalarda yeniden deneyerek çağırır.

    Başarılı olursa sonucu döner. Geçici hata + denemeler tükendi ->
    `ServiceUnavailableError` (503). Kalıcı/beklenmedik hata ->
    `UpstreamServiceError` (502).
    """
    son_hata: Exception | None = None
    for deneme in range(settings.gemini_max_retries + 1):
        try:
            return fn()
        except Exception as hata:  # noqa: BLE001 — sınıflandırıp yeniden fırlatıyoruz
            son_hata = hata
            son_deneme = deneme >= settings.gemini_max_retries
            if _gecici_mi(hata) and not son_deneme:
                gecikme = _backoff_suresi(deneme)
                logger.warning(
                    "gemini_transient_retry",
                    extra={
                        "islem": islem,
                        "deneme": deneme + 1,
                        "kod": getattr(hata, "code", None),
                        "gecikme_s": round(gecikme, 2),
                    },
                )
                time.sleep(gecikme)
                continue
            break

    # Döngü başarısız bitti: hatayı sınıflandır.
    assert son_hata is not None
    if _gecici_mi(son_hata):
        logger.error(
            "gemini_unavailable_retries_exhausted",
            extra={"islem": islem, "kod": getattr(son_hata, "code", None)},
            exc_info=son_hata,
        )
        raise ServiceUnavailableError() from son_hata

    logger.error("gemini_failed", extra={"islem": islem}, exc_info=son_hata)
    raise UpstreamServiceError() from son_hata


def _strip_json_fence(metin: str) -> str:
    """Modelin döndürdüğü ```json ... ``` çitini temizler."""
    metin = metin.strip()
    if metin.startswith("```json"):
        return metin.removeprefix("```json").removesuffix("```").strip()
    if metin.startswith("```"):
        return metin.removeprefix("```").removesuffix("```").strip()
    return metin


def json_uret(prompt: str, model: str | None = None) -> dict:
    """Prompt gönder, JSON yanıtı Python dict olarak döndür.

    Geçici API hatası retry ile denenir; tükenirse `ServiceUnavailableError`.
    Kalıcı hata veya geçersiz JSON -> `UpstreamServiceError`.
    """
    model = model or settings.gemini_json_model
    yanit = _retry_ile_cagir(
        lambda: _client().models.generate_content(model=model, contents=prompt),
        islem="generate_content(json)",
    )

    ham = _strip_json_fence(yanit.text or "")
    try:
        return json.loads(ham)
    except json.JSONDecodeError as hata:
        logger.error("gemini_json_parse_failed", extra={"model": model}, exc_info=hata)
        raise UpstreamServiceError("Yapay zeka geçersiz bir yanıt üretti.") from hata


def metin_uret(prompt: str, model: str | None = None) -> str:
    """Prompt gönder, düz metin yanıtı döndür. (Geçici hatalarda retry.)"""
    model = model or settings.gemini_text_model
    yanit = _retry_ile_cagir(
        lambda: _client().models.generate_content(model=model, contents=prompt),
        islem="generate_content(text)",
    )
    return (yanit.text or "").strip()


def embedding_uret(
    metin: str, gorev_tipi: str = "RETRIEVAL_DOCUMENT"
) -> list[float] | None:
    """Metni embedding vektörüne çevirir.

    gorev_tipi:
        RETRIEVAL_DOCUMENT -> saklanan belgeler (CV, ilan)
        RETRIEVAL_QUERY    -> arama sorgusu

    Geçici hatalarda retry yapılır (başarı şansını artırır), ama sonuçta
    başarısız olursa `None` döner (graceful degradation): embedding kolonu
    nullable olduğundan çağıran taraf embedding'siz de kaydedebilir. Embedding
    "olsa iyi olur" bir alandır, kaydı bloklamamalı — bu yüzden exception
    yutulur.
    """
    if not metin or not metin.strip():
        return None
    try:
        yanit = _retry_ile_cagir(
            lambda: _client().models.embed_content(
                model=settings.gemini_embedding_model,
                contents=metin,
                config=types.EmbedContentConfig(
                    task_type=gorev_tipi,
                    output_dimensionality=settings.embedding_dim,
                ),
            ),
            islem="embed_content",
        )
        return yanit.embeddings[0].values
    except (ServiceUnavailableError, UpstreamServiceError):
        # retry'lar zaten loglandı; embedding opsiyonel olduğundan None dön.
        logger.warning("embedding_failed_after_retries")
        return None
