from __future__ import annotations

from time import perf_counter

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
    lms_context: str | None = None  # text context directly injected from the web page


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

    t_rag = perf_counter()
    if body.lms_context and body.lms_context.strip():
        # Context Injection takes priority over RAG
        context = body.lms_context.strip()
        rag_ms = (perf_counter() - t_rag) * 1000
        
        system_prompt = (
            "Anda adalah Viona, asisten virtual cerdas untuk LMS Bengkel Koding.\n"
            "Tugas utama Anda adalah membantu menjawab pertanyaan siswa MURNI BERDASARKAN "
            "materi pelajaran yang sedang mereka buka di layar.\n\n"
            "ATURAN KETAT (PENTING):\n"
            "1. Jika pertanyaan siswa BISA DIJAWAB menggunakan informasi pada KONTEKS MATERI, "
            "berikan jawaban yang jelas dan edukatif berdasarkan teks tersebut.\n"
            "2. Jika pertanyaan siswa SAMA SEKALI TIDAK ADA di dalam KONTEKS MATERI, Anda DILARANG KERAS "
            "menggunakan pengetahuan umum Anda untuk menjawab. Anda HARUS MENOLAK dengan ramah "
            "dan menyatakan bahwa pertanyaan tersebut berada di luar materi yang sedang dibaca.\n"
            "3. JANGAN PERNAH memulai jawaban dengan sapaan seperti 'Halo' atau memperkenalkan diri.\n"
            "4. JANGAN menebak-nebak jawaban."
        )
        context_block = f"KONTEKS MATERI LMS SAAT INI:\n{context}\n\n"
    else:
        context = await _retrieve_context(body.message, body.material_id, body.version)
        rag_ms = (perf_counter() - t_rag) * 1000

        if not context:
            system_prompt = (
                "Anda adalah Viona, asisten virtual yang ramah dan berbahasa Indonesia.\n"
                "Konteks dari database kosong. Silakan jawab pertanyaan pengguna menggunakan "
                "pengetahuan umum Anda secara ringkas, jujur, dan edukatif.\n\n"
                "ATURAN PENTING:\n"
                "- JANGAN PERNAH memulai jawaban dengan sapaan seperti 'Halo' atau memperkenalkan diri (misal 'Saya Viona').\n"
                "- Langsung berikan jawaban dari pertanyaan yang diajukan tanpa basa-basi pengenalan diri."
            )
        else:
            system_prompt = (
                "Anda adalah Viona, asisten virtual LMS yang membantu, ramah, dan berbicara "
                "dengan bahasa Indonesia yang natural.\n"
                "Gunakan informasi pada bagian KONTEKS untuk menjawab bila relevan. "
                "Jika konteks tidak memuat jawabannya, Anda DIPERBOLEHKAN menggunakan "
                "pengetahuan umum Anda sendiri untuk menjawab pertanyaan dengan jujur, "
                "edukatif, dan sopan.\n\n"
                "ATURAN PENTING:\n"
                "- JANGAN PERNAH memulai jawaban dengan sapaan seperti 'Halo' atau memperkenalkan diri (misal 'Saya Viona').\n"
                "- Langsung berikan jawaban dari pertanyaan yang diajukan tanpa basa-basi pengenalan diri."
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

    t_llm = perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Tanpa try-except pelindung agar error asli (misal timeout/connection refused)
        # meledak ke terminal (HTTP 500) dan log dapat terlihat jelas untuk debugging!
        response = await client.post(ollama_url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        # /api/chat returns {"message": {"role": "assistant", "content": "..."}}
        msg = data.get("message", {})
        reply = msg.get("content", "").strip() if isinstance(msg, dict) else ""

    llm_wall_ms = (perf_counter() - t_llm) * 1000

    # Ollama /api/chat mengembalikan field timing dalam NANODETIK. Ini memisahkan
    # waktu generasi ASLI (eval_duration) dari pemrosesan prompt & overhead jaringan
    # (llm_wall_ms). eval_count = jumlah token output → tokens/sec. Lihat docs/TIMING.md.
    def _ms(ns: int | None) -> float | None:
        return round(ns / 1e6, 1) if ns else None

    gen_ms = _ms(data.get("eval_duration"))
    prompt_ms = _ms(data.get("prompt_eval_duration"))
    total_ms = _ms(data.get("total_duration"))
    out_tokens = data.get("eval_count")
    tok_per_s = (
        round(out_tokens / (data["eval_duration"] / 1e9), 1)
        if out_tokens and data.get("eval_duration")
        else None
    )
    # Cloud-routed models (e.g. *-cloud) return 0 for eval_duration/prompt_eval_duration,
    # so gen_ms/prompt_ms/tok_per_s are None. Effective throughput from wall-clock stays
    # meaningful for both cloud and local. See docs/TIMING.md.
    eff_tok_per_s = (
        round(out_tokens / (llm_wall_ms / 1000), 1) if out_tokens and llm_wall_ms else None
    )

    logger.info(
        "chat timing",
        rag_ms=round(rag_ms, 1),
        llm_wall_ms=round(llm_wall_ms, 1),
        gen_ms=gen_ms,
        prompt_ms=prompt_ms,
        tok_per_s=tok_per_s,
        eff_tok_per_s=eff_tok_per_s,
        out_tokens=out_tokens,
        out_chars=len(reply),
        has_context=bool(context),
    )
    return {
        "response": reply,
        "status": "ok",
        "timings_ms": {
            "rag": round(rag_ms, 1),
            "llm_wall": round(llm_wall_ms, 1),
            "llm_generation": gen_ms,
            "llm_prompt_eval": prompt_ms,
            "llm_total": total_ms,
            "tokens_per_sec": tok_per_s,
            "eff_tokens_per_sec": eff_tok_per_s,
        },
    }
