"""Yapılandırılmış logging kurulumu.

`print()` yerine standart `logging` kullanılır. Development'ta okunabilir
düz metin, production'da (LOG_JSON=true) tek satırlık JSON üretir — böylece
log aggregation araçları (Loki, CloudWatch, Datadog) alanları ayrıştırabilir.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

from app.core.config import settings

# Request başına atanan korelasyon kimliği. Middleware set eder; loglar okur.
# ContextVar olduğu için thread/async bağlamları arasında sızmaz.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Her log kaydına aktif request_id'yi ekler."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Log kaydını tek satırlık JSON'a çevirir."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Ekstra alanlar (logger.info(..., extra={...})) korunur.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime"}


def setup_logging() -> None:
    """Kök logger'ı yapılandır. Uygulama açılışında bir kez çağrılır."""
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Idempotent: reload/testte handler birikmesin.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | [%(request_id)s] | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root.addHandler(handler)

    # Uvicorn'un kendi erişim logu gürültüsünü kısar (opsiyonel).
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
