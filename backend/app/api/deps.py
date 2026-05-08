from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.infrastructure.session.store import SessionStore, get_session_store


async def _get_store() -> SessionStore:
    return await get_session_store()


StoreDep = Annotated[SessionStore, Depends(_get_store)]
