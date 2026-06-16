from __future__ import annotations

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.infrastructure.rag.retriever import get_rag_retriever

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    material_id: str | None = None  # filter RAG per-materi LMS (mis. "matematika")
    version: str | None = None      # filter RAG per-versi (mis. "v1")


async def _retrieve_context(query: str, material_id: str | None, version: str | None) -> str:
    """Ambil konteks relevan dari basis pengetahuan (RAG). Gagal-aman: kalau RAG
    bermasalah, kembalikan string kosong agar chat tetap jalan (degradasi mulus)."""
    try:
        retriever = await get_rag_retriever()
        hits = await retriever.search(
            query,
            material_id=material_id,
            version=version,
            top_k=3,
            score_threshold=0.45,
        )
    except Exception as e:
        logger.warning("rag retrieval failed, lanjut tanpa konteks", error=str(e))
        return ""

    if not hits:
        return ""
    return "\n".join(f"- {h['text']}" for h in hits)


@router.post("")
async def chat_with_viona(body: ChatRequest) -> dict:
    """Chat dengan Viona: RAG (Qdrant) + LLM (Ollama native API)."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty")

    context = await _retrieve_context(body.message, body.material_id, body.version)

    if not context:
        system_prompt = (
            "Anda adalah Viona, asisten virtual yang ramah dan berbahasa Indonesia.\n"
            "Konteks dari database kosong. Silakan jawab pertanyaan pengguna menggunakan "
            "pengetahuan umum Anda secara ringkas, jujur, dan edukatif."
        )
    else:
        system_prompt = (
            "Anda adalah Viona, asisten virtual LMS yang membantu, ramah, dan berbicara "
            "dengan bahasa Indonesia yang natural.\n"
            "Gunakan informasi pada bagian KONTEKS untuk menjawab bila relevan. "
            "Jika konteks tidak memuat jawabannya, Anda DIPERBOLEHKAN menggunakan pengetahuan umum Anda "
            "sendiri untuk menjawab pertanyaan dengan jujur, edukatif, dan sopan."
        )

    context_block = (
        f"KONTEKS:\n{context}\n\n"
        if context
        else ""
    )

    # Gunakan native Ollama API (/api/chat)
    ollama_url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_block}{body.message}"},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.7,
        },
    }

    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Tanpa try-except pelindung agar error asli (misal timeout/connection refused)
        # meledak ke terminal (HTTP 500) dan log dapat terlihat jelas untuk debugging!
        response = await client.post(ollama_url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        # /api/chat returns {"message": {"role": "assistant", "content": "..."}}
        msg = data.get("message", {})
        reply = msg.get("content", "").strip() if isinstance(msg, dict) else ""
        return {"response": reply, "status": "ok"}
