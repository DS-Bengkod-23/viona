from __future__ import annotations

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_KEY_PREFIX = "viona:session:"


class SessionStore:
    """Async Redis-backed session storage."""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    def _require(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("SessionStore not connected – call connect() first")
        return self._redis

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
        )
        await self._redis.ping()
        logger.info("redis connected", url=settings.redis_url)

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def get(self, session_id: str) -> dict[str, Any]:
        raw = await self._require().get(self._key(session_id))
        return json.loads(raw) if raw else {}

    async def set(self, session_id: str, data: dict[str, Any]) -> None:
        await self._require().setex(
            self._key(session_id),
            settings.redis_session_ttl,
            json.dumps(data, ensure_ascii=False),
        )

    async def update(self, session_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        data = await self.get(session_id)
        data.update(updates)
        await self.set(session_id, data)
        return data

    async def delete(self, session_id: str) -> None:
        await self._require().delete(self._key(session_id))

    async def exists(self, session_id: str) -> bool:
        return bool(await self._require().exists(self._key(session_id)))

    async def log_interaction(self, session_id: str, role: str, text: str, image: str | None = None) -> None:
        data = await self.get(session_id)
        history: list[dict] = data.get("history", [])
        entry = {"role": role, "text": text}
        if image:
            entry["image"] = image
        history.append(entry)
        data["history"] = history[-50:]
        await self.set(session_id, data)


_store: SessionStore | None = None
_store_lock = asyncio.Lock()


async def get_session_store() -> SessionStore:
    global _store
    if _store is not None:
        return _store
    async with _store_lock:
        if _store is None:
            _store = SessionStore()
            await _store.connect()
    return _store


async def shutdown_session_store() -> None:
    global _store
    if _store is not None:
        await _store.disconnect()
        _store = None
