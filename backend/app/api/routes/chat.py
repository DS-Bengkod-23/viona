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

    system_prompt = (
        "Anda adalah Viona, asisten virtual LMS yang membantu, ramah, dan berbicara "
        "dengan bahasa Indonesia yang natural.\n"
        "Gunakan informasi pada bagian KONTEKS untuk menjawab bila relevan. "
        "Jika konteks tidak memuat jawabannya, jawab sejujurnya dan sopan tanpa mengarang."
    )

    context_block = (
        f"KONTEKS:\n{context}\n\n"
        if context
        else "KONTEKS: (tidak ada dokumen panduan spesifik yang ditemukan)\n\n"
    )

    # Use Ollama native API endpoint. Base URL: http://ollama:11434 (from .env)
    ollama_url = f"{settings.ollama_base_url}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "prompt": f"System: {system_prompt}\n\n{context_block}User: {body.message}\n",
        "stream": False,
        "options": {
            "temperature": 0.7,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(ollama_url, json=payload)
            if response.status_code != 200:
                logger.error("ollama error response", status=response.status_code, body=response.text)
                raise HTTPException(status_code=502, detail="Error communicating with LLM service")

            data = response.json()
            reply = data.get("response", "").strip()
            return {"response": reply, "status": "ok"}
    except httpx.RequestError as e:
        logger.error("ollama request failed", error=str(e))
        raise HTTPException(status_code=502, detail="LLM service is unreachable")
