"""Yapılandırılmış logging kurulumu.

`print()` yerine standart `logging` kullanılır. Development'ta okunabilir
düz metin, production'da (LOG_JSON=true) tek satırlık JSON üretir — böylece
log aggregation araçları (Loki, CloudWatch, Datadog) alanları ayrıştırabilir.
"""

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Log kaydını tek satırlık JSON'a çevirir."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
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
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root.addHandler(handler)

    # Uvicorn'un kendi erişim logu gürültüsünü kısar (opsiyonel).
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
