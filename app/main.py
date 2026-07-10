"""FastAPI uygulama fabrikası (application factory).

`create_app()` deseni: uygulama nesnesi bir fonksiyonda kurulur. Test'te
farklı yapılandırmayla yeniden üretilebilir, import yan etkisi azalır.

Not: Şema, `Base.metadata.create_all` ile değil Alembic migration'larıyla
yönetilir (`alembic upgrade head`). Böylece şema değişimleri versiyonlanır ve
geri alınabilir.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.routers import cv, health, ilan, mektup, oneri, uyum


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger(__name__)
    logger.info(
        "app_startup",
        extra={"version": settings.app_version, "env": settings.environment},
    )
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        # Production'da OpenAPI dokümanını kapatmak istersen:
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    for router in (health, cv, ilan, uyum, mektup, oneri):
        app.include_router(router.router)

    return app


app = create_app()
