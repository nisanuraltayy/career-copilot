"""Rate limiting (slowapi).

AI endpoint'leri Gemini'ye para/kota maliyeti taşır; kötüye kullanımı ve
kaza sonucu döngüleri sınırlamak için istek başına IP bazlı limit uygulanır.

Not: Uygulama bir reverse proxy (nginx) arkasındaysa gerçek istemci IP'si
`X-Forwarded-For` başlığındadır. slowapi'nin varsayılan `get_remote_address`
fonksiyonu `request.client.host`'u kullanır; proxy arkasında proxy'nin
forwarded IP'yi doğru ilettiğinden emin olun (nginx conf'ta ayarlı).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    # headers_enabled=False: slowapi, rate-limit başlıklarını enjekte etmek için
    # endpoint'in bir `Response` döndürmesini bekler; bizim uçlarımız Pydantic
    # model döndürüyor. Açık bırakılırsa TÜM rate-limitli uçlar 500 verir.
    # Limit yine uygulanır (aşımda 429), sadece X-RateLimit-* başlıkları olmaz.
    headers_enabled=False,
)
