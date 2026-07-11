"""Uygulama hata hiyerarşisi ve FastAPI exception handler'ları.

Amaç: iş mantığı katmanı, HTTP'den bağımsız anlamlı hatalar fırlatsın
(`ResourceNotFound`, `UpstreamServiceError` ...). Router'lar bunları
yakalamak zorunda kalmaz; merkezi handler'lar tutarlı JSON gövdesine çevirir.

Client'a asla ham stack trace / `str(exception)` sızmaz — teknik detay
sadece sunucu logunda kalır.
"""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Tüm uygulama hatalarının tabanı."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    message: str = "Beklenmeyen bir hata oluştu."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class ResourceNotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    message = "Kaynak bulunamadı."


class ValidationFailed(AppError):
    status_code = 422
    error_code = "validation_failed"
    message = "Geçersiz istek."


class UpstreamServiceError(AppError):
    """Dış servis kalıcı/beklenmedik bir hata verdiğinde (geçici değil).

    Örn: geçersiz yanıt, 4xx istemci hatası. 502 Bad Gateway.
    """

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "upstream_error"
    message = "Yapay zeka servisine ulaşılamadı, lütfen tekrar deneyin."


class ServiceUnavailableError(AppError):
    """Dış servis GEÇİCİ olarak uygun değil ve yeniden denemeler tükendi.

    Örn: yoğun trafikte tekrarlayan 503 UNAVAILABLE / 429. 503 Service
    Unavailable — istemci birkaç saniye sonra tekrar denemelidir.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "service_unavailable"
    message = "The AI service is temporarily busy. Please try again in a few seconds."


class AuthError(AppError):
    """Kimlik doğrulama başarısız (token yok/geçersiz, parola yanlış)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"
    message = "Kimlik doğrulaması gerekli."


class ConflictError(AppError):
    """Kaynak çakışması (örn. e-posta zaten kayıtlı)."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    message = "Kaynak zaten mevcut."


class BusinessRuleError(AppError):
    """İş kuralı ihlali (örn. embedding'i olmayan CV için öneri istenmesi)."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "business_rule"
    message = "İşlem bu kaynak için gerçekleştirilemez."


def _error_body(error_code: str, message: str) -> dict:
    return {"error": {"code": error_code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # 5xx sunucu tarafı; stack trace ile logla. 4xx bilgi amaçlı.
        if exc.status_code >= 500:
            logger.error(
                "app_error", extra={"path": request.url.path, "code": exc.error_code},
                exc_info=exc,
            )
        else:
            logger.info(
                "app_error", extra={"path": request.url.path, "code": exc.error_code},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_failed",
                    "message": "İstek doğrulanamadı.",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Beklenmeyen her şey: detay logda, client'a genel mesaj.
        logger.error(
            "unhandled_exception",
            extra={"path": request.url.path},
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "Beklenmeyen bir hata oluştu."),
        )
