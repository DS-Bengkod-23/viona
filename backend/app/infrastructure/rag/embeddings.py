from __future__ import annotations

from typing import Sequence

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Embedding di-offload ke container Ollama via HTTP (/api/embed) agar onnxruntime
# tidak berjalan in-process — ini menghilangkan ledakan memori/OOM yang terjadi saat
# fastembed + qdrant-client hidup berdampingan di lingkungan ARM/Docker.
_EMBED_URL = f"{settings.ollama_base_url.rstrip('/')}/api/embed"

_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)

# Fallback dimensi bila override config kosong DAN deteksi runtime gagal.
# (qwen3-embedding:0.6b = 1024-dim.)
_FALLBACK_EMBEDDING_DIM = 1024

# Cache hasil deteksi dimensi (diisi sekali saat pemanggilan pertama).
_embedding_dim: int | None = None


async def get_embedding_dim() -> int:
    """Dimensi vektor embedding (di-cache).

    Prioritas: ``settings.embedding_dim`` (override eksplisit) → deteksi otomatis via
    Ollama (panjang vektor probe) → ``_FALLBACK_EMBEDDING_DIM``. Membuat ukuran
    collection Qdrant portabel lintas model embedding tanpa edit kode.
    """
    global _embedding_dim
    if settings.embedding_dim:
        return settings.embedding_dim
    if _embedding_dim is None:
        try:
            probe = await embed_query("dimension probe")
            _embedding_dim = len(probe)
            logger.info("embedding dim detected", dim=_embedding_dim, model=settings.embedding_model)
        except Exception as e:  # noqa: BLE001 - deteksi gagal → pakai fallback
            _embedding_dim = _FALLBACK_EMBEDDING_DIM
            logger.warning("embedding dim detection failed, pakai fallback", dim=_embedding_dim, error=str(e))
    return _embedding_dim


def init_embedding_model() -> None:
    """Kompatibilitas API lama. Kini embedding di Ollama, jadi tidak ada model yang
    di-load in-process. Disengaja dibuat no-op ringan; warm-up dilakukan async di
    startup (lihat app.py) lewat embed_query.
    """
    logger.info("embedding backend: ollama", url=_EMBED_URL, model=settings.embedding_model)


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed satu atau banyak teks via Ollama /api/embed."""
    payload = {"model": settings.embedding_model, "input": list(texts)}
    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"
    # Client dibuat per-panggilan (bukan modul-level): httpx.AsyncClient terikat ke
    # event loop saat dibuat; reuse lintas loop (startup vs request uvicorn) bikin hang.
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(_EMBED_URL, json=payload, headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error("ollama embed http error", status=e.response.status_code, body=e.response.text[:300])
        raise
    except httpx.RequestError as e:
        logger.error("ollama embed request failed", error=str(e), url=_EMBED_URL)
        raise

    data = resp.json()
    embeddings = data.get("embeddings")
    if not embeddings:
        logger.error("ollama embed: empty response", body=str(data)[:300])
        raise ValueError("Ollama returned no embeddings")
    return embeddings


async def embed_query(text: str) -> list[float]:
    results = await embed_texts([text])
    return results[0]
