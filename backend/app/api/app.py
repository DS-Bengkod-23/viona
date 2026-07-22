from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, health, ingestion, sessions, token, tts
from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.rag.retriever import get_rag_retriever
from app.infrastructure.session.store import get_session_store, shutdown_session_store

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("initializing services...")
    await get_session_store()

    # Embedding di-offload ke Ollama (HTTP). Warm-up ringan: satu panggilan embed
    # untuk memastikan model embedding (default: qwen3-embedding:0.6b) di Ollama
    # responsif. Tidak memblokir/OOM karena inferensi terjadi di container Ollama.
    try:
        from app.infrastructure.rag.embeddings import embed_query, init_embedding_model
        init_embedding_model()
        await asyncio.wait_for(embed_query("warmup"), timeout=30)
        logger.info("embedding backend ready")
    except Exception as e:
        logger.warning("embedding warm-up failed", error=str(e))

    # Inisialisasi retriever (memastikan koleksi Qdrant ada) sekali saat startup.
    try:
        await asyncio.wait_for(get_rag_retriever(), timeout=30)
        logger.info("retriever ready")
    except Exception as e:
        logger.warning("retriever init failed", error=str(e))

    logger.info("api started", host=settings.api_host, port=settings.api_port)
    yield
    await shutdown_session_store()


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Viona Voice AI API",
        version="1.0.0",
        description="Indonesian voice AI learning companion backend",
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
    app.include_router(chat.router)
    app.include_router(tts.router)

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
