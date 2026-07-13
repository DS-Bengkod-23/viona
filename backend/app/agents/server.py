"""Agent dispatch server (VIONA_MODE=agent).

A lightweight FastAPI app that receives LiveKit webhooks and spawns a Pipecat
bot per room. Replaces the LiveKit Agents `cli.run_app` worker. Runs on port
8081 (the same port the old worker exposed for health/metrics).

LiveKit must be configured to POST room events to ``/webhooks/livekit``.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, Header, Request, Form
from fastapi.responses import Response
from livekit.api import TokenVerifier, WebhookReceiver

from app.agents.pipecat_worker import BOT_IDENTITY, run_bot_for_room
from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.metrics.prometheus import metrics_output
from app.infrastructure.rag.retriever import get_rag_retriever
from app.infrastructure.session.store import get_session_store

logger = structlog.get_logger(__name__)

_webhook_receiver = WebhookReceiver(
    TokenVerifier(settings.livekit_api_key, settings.livekit_api_secret)
)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    await get_session_store()
    try:
        await asyncio.wait_for(get_rag_retriever(), timeout=30)
    except Exception as exc:  # noqa: BLE001 - retriever is best-effort at boot
        logger.warning("rag retriever warmup skipped", error=str(exc))
    logger.info("agent dispatch server ready")
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Viona Agent Dispatch", lifespan=_lifespan)

    @app.get("/")
    async def root() -> dict:
        return {"status": "ok", "service": "viona-agent"}

    @app.get("/metrics")
    async def metrics() -> Response:
        body, content_type = metrics_output()
        return Response(content=body, media_type=content_type)

    @app.post("/dev/spawn")
    async def dev_spawn(room_name: str = Form(...), identity: str = Form(...), lms_context: str = Form("")) -> dict:
        logger.info("dev spawn triggered", room=room_name, identity=identity)
        asyncio.create_task(_spawn(room_name, identity, lms_context))
        return {"spawned": True}

    @app.post("/webhooks/livekit")
    async def livekit_webhook(
        request: Request, authorization: str = Header(default="")
    ) -> dict:
        body = (await request.body()).decode("utf-8")
        try:
            event = _webhook_receiver.receive(body, authorization)
        except Exception as exc:  # noqa: BLE001 - reject unverified/garbled payloads
            logger.warning("livekit webhook verify failed", error=str(exc))
            return {"received": False}

        room_name = event.room.name if event.room else ""
        identity = event.participant.identity if event.participant else ""

        # Spawn a bot when a human caller joins (ignore the bot's own join).
        if event.event == "participant_joined" and identity != BOT_IDENTITY and room_name:
            logger.info("caller joined, spawning bot", room=room_name, identity=identity)
            # When spawned via LiveKit webhook directly, lms_context is empty
            asyncio.create_task(_spawn(room_name, identity, ""))

        return {"received": True}

    return app


async def _spawn(room_name: str, identity: str, lms_context: str = "") -> None:
    try:
        await run_bot_for_room(room_name, customer_phone=identity, lms_context=lms_context)
    except Exception as exc:  # noqa: BLE001
        logger.error("bot run failed", room=room_name, error=str(exc))


def main() -> None:
    configure_logging()
    uvicorn.run(create_app(), host="0.0.0.0", port=8081)


if __name__ == "__main__":
    main()
