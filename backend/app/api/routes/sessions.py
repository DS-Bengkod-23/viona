from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.infrastructure.session.store import get_session_store

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    store = await get_session_store()
    data = await store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict:
    store = await get_session_store()
    if not await store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    await store.delete(session_id)
    return {"deleted": session_id}


@router.get("/{session_id}/history")
async def get_session_history(session_id: str) -> dict:
    store = await get_session_store()
    data = await store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": data.get("history", [])}
