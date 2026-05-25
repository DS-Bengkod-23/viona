from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, ingestion, sessions, token, webhooks, chat
from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.rag.retriever import get_rag_retriever
from app.infrastructure.session.store import get_session_store, shutdown_session_store

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    await get_session_store()
    await get_rag_retriever()
    logger.info("api started", host=settings.api_host, port=settings.api_port)
    yield
    await shutdown_session_store()


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Viona Voice AI API",
        version="1.0.0",
        description="Indonesian realtime voice AI customer support backend",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled error", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health.router)
    app.include_router(token.router)
    app.include_router(sessions.router)
    app.include_router(ingestion.router)
    app.include_router(webhooks.router)
    app.include_router(chat.router)

    return app


application = create_app()


def main() -> None:
    uvicorn.run(
        "app.api.app:application",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment != "production",
        log_config=None,
    )


if __name__ == "__main__":
    main()
