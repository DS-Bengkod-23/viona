from __future__ import annotations

from time import perf_counter

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.text_cleaner import normalize_for_tts

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/tts", tags=["tts"])

# Batas aman panjang teks per permintaan. Jawaban Viona ditarget 2-3 kalimat
# (_BREVITY_INSTRUCTION di chat.py), jadi ini hanya jaring pengaman biaya/latensi.
_MAX_CHARS = 2000

_CARTESIA_URL = "https://api.cartesia.ai/tts/bytes"
# Samakan dengan versi yang dipakai pipecat.services.cartesia (path LiveKit),
# supaya kedua jalur suara bicara ke kontrak API yang sama.
_CARTESIA_VERSION = "2026-03-01"


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)


@router.post("")
async def synthesize(body: TTSRequest) -> Response:
    """Sintesis suara via Cartesia untuk jalur native (browser).

    Kunci Cartesia SENGAJA tidak pernah dikirim ke browser: frontend memanggil
    endpoint ini, server yang memanggil Cartesia. Balasannya audio mp3 mentah.

    Kegagalan dikembalikan sebagai 5xx supaya frontend bisa fallback ke Web
    Speech API dan suara tetap ada walau Cartesia sedang bermasalah.
    """
    if not settings.cartesia_api_key:
        raise HTTPException(status_code=503, detail="CARTESIA_API_KEY belum diset")

    # Rapikan LaTeX/simbol matematika jadi kata terucap. Ini pertama kalinya
    # normalize_for_tts() terpasang di jalur TTS yang benar-benar aktif
    # (sebelumnya hanya dipakai VoxCPM2 yang diparkir).
    text = normalize_for_tts(body.text.strip())[:_MAX_CHARS]
    if not text:
        raise HTTPException(status_code=400, detail="teks kosong setelah normalisasi")

    payload = {
        "model_id": settings.cartesia_model,
        "transcript": text,
        "voice": {"mode": "id", "id": settings.cartesia_voice_id},
        # mp3 dipilih (bukan wav/raw) supaya payload kecil di jaringan dan
        # langsung bisa diputar <audio> browser tanpa dekode manual.
        "output_format": {"container": "mp3", "sample_rate": 44100, "bit_rate": 128000},
        "language": "id",
    }
    headers = {
        "Cartesia-Version": _CARTESIA_VERSION,
        # Dokumentasi Cartesia menyebut Bearer sebagai cara resmi; pipecat masih
        # memakai header lama "X-API-Key" (tampaknya tetap diterima). Keduanya sudah
        # diuji dan sama-sama 401 saat key tidak valid, jadi ini bukan pembeda —
        # kalau suatu saat auth bermasalah, tukar ke X-API-Key layak dicoba.
        "Authorization": f"Bearer {settings.cartesia_api_key}",
        "Content-Type": "application/json",
    }

    t0 = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_CARTESIA_URL, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("tts request failed", error=str(exc))
        raise HTTPException(status_code=503, detail="TTS tidak dapat dihubungi") from exc

    if resp.status_code != 200:
        # Jangan teruskan isi error Cartesia apa adanya ke klien (bisa memuat
        # detail akun); cukup dicatat di log server.
        logger.warning("tts upstream error", status=resp.status_code, body=resp.text[:300])
        raise HTTPException(status_code=502, detail="TTS gagal mensintesis suara")

    audio = resp.content
    elapsed_ms = (perf_counter() - t0) * 1000
    logger.info("tts timing", ms=round(elapsed_ms, 1), chars=len(text), bytes=len(audio))

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "X-TTS-Ms": str(round(elapsed_ms, 1)),
        },
    )
