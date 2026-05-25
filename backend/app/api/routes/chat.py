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
    material_id: str | None = None
    version: str | None = None


@router.post("")
async def chat_with_viona(body: ChatRequest) -> dict:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty")

    # 1. Cari berkas corpus yang relevan via Qdrant (RAG)
    retriever = await get_rag_retriever()
    hits = await retriever.search(
        query=body.message,
        material_id=body.material_id,
        version=body.version,
        top_k=3,
        score_threshold=0.45,
    )

    # 2. Susun context dari hits
    context = "\n".join([f"- {h['text']}" for h in hits]) if hits else "Tidak ada dokumen panduan spesifik yang ditemukan."

    # 3. Susun prompt untuk LLM
    system_prompt = (
        "Anda adalah Viona, asisten virtual LMS yang membantu, ramah, dan berbicara dengan bahasa Indonesia yang natural.\n"
        "Gunakan informasi pendukung berikut untuk menjawab pertanyaan pengguna. Jika informasi pendukung tidak mencukupi, jawablah sebaik mungkin sesuai kemampuan Anda.\n\n"
        f"Informasi Pendukung:\n{context}"
    )

    # 4. Hubungi Ollama secara asinkron
    # Kita panggil endpoint /api/generate bawaan Ollama
    ollama_url = f"{settings.ollama_base_url.rstrip('/v1')}/api/generate"
    # Fallback jika URL default internal:
    if "ollama:11434" in ollama_url:
        ollama_url = "http://ollama:11434/api/generate"

    payload = {
        "model": "llama3.2:3b" if "gpt-oss" in settings.ollama_model else settings.ollama_model,
        "prompt": f"System: {system_prompt}\nUser: {body.message}",
        "stream": False,
        "options": {
            "temperature": 0.7,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(ollama_url, json=payload)
            if response.status_code != 200:
                logger.error("ollama error response", status=response.status_code, body=response.text)
                raise HTTPException(status_code=502, detail="Error communicating with LLM service")
            
            data = response.json()
            reply = data.get("response", "").strip()
            return {"response": reply, "status": "ok", "context_used": len(hits)}
    except httpx.RequestError as e:
        logger.error("ollama request failed", error=str(e))
        raise HTTPException(status_code=502, detail="LLM service is unreachable")
