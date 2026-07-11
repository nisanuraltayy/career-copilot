"""HTTP middleware'leri: request-ID korelasyonu ve güvenlik başlıkları."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Her isteğe bir korelasyon kimliği atar.

    - Gelen `X-Request-ID` başlığı varsa onu kullanır (upstream proxy zinciri),
      yoksa yeni bir UUID üretir.
    - ContextVar'a yazar → tüm loglar bu istekle ilişkilendirilir.
    - Yanıta `X-Request-ID` başlığı ekler → client/istemci hata bildiriminde
      referans verebilir.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Temel güvenlik başlıkları (ucuz, iyi varsayılanlar)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response
