from __future__ import annotations

import asyncio

import httpx
import structlog

from app.core.config import settings
from app.infrastructure.rag.embeddings import embed_query, get_embedding_dim

logger = structlog.get_logger(__name__)


class RAGRetriever:
    """Semantic retriever backed by Qdrant.

    Memakai REST API Qdrant lewat httpx (bukan library qdrant-client) karena client
    async qdrant-client tidak stabil di lingkungan ARM/Docker (hang/crash native saat
    dipakai dari dalam proses uvicorn). REST + httpx sederhana dan andal.
    """

    def __init__(self) -> None:
        self._base = settings.qdrant_url.rstrip("/")
        self._collection = settings.qdrant_collection
        self._headers = {}
        if settings.qdrant_api_key:
            self._headers["api-key"] = settings.qdrant_api_key
        self._timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)

    def _make_client(self) -> httpx.AsyncClient:
        # Per-panggilan: httpx.AsyncClient terikat ke event loop saat dibuat; reuse
        # lintas loop (startup vs request uvicorn) menyebabkan hang.
        return httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=self._timeout)

    async def ensure_collection(self) -> None:
        async with self._make_client() as client:
            resp = await client.get(f"/collections/{self._collection}")
            if resp.status_code == 200:
                return
            # 404 → belum ada, buat. Status lain → angkat error.
            if resp.status_code != 404:
                resp.raise_for_status()
            dim = await get_embedding_dim()
            create = await client.put(
                f"/collections/{self._collection}",
                json={"vectors": {"size": dim, "distance": "Cosine"}},
            )
            create.raise_for_status()
        logger.info("qdrant collection created", collection=self._collection, dim=dim)

    async def search(
        self,
        query: str,
        *,
        material_id: str | None = None,
        version: str | None = None,
        top_k: int = 4,
        score_threshold: float = 0.60,
    ) -> list[dict]:
        vector = await embed_query(query)

        conditions = []
        if material_id:
            conditions.append({"key": "material_id", "match": {"value": material_id}})
        if version:
            conditions.append({"key": "version", "match": {"value": version}})

        body: dict = {
            "vector": vector,
            "limit": top_k,
            "score_threshold": score_threshold,
            "with_payload": True,
        }
        if conditions:
            body["filter"] = {"must": conditions}

        async with self._make_client() as client:
            resp = await client.post(
                f"/collections/{self._collection}/points/search", json=body
            )
        resp.raise_for_status()
        hits = resp.json().get("result", [])

        results: list[dict] = []
        seen: set[str] = set()
        for hit in hits:
            payload = hit.get("payload") or {}
            text: str = payload.get("text", "")
            if text in seen:
                continue
            seen.add(text)
            results.append({
                "id": str(hit.get("id")),
                "score": round(hit.get("score", 0.0), 4),
                "text": text,
                "source": payload.get("source", ""),
                "category": payload.get("category", ""),
            })

        logger.debug("rag search", query=query[:60], hits=len(results))
        return results

    async def upsert(self, points: list[dict]) -> None:
        # points: list of {"id", "vector", "payload"} — format REST Qdrant.
        async with self._make_client() as client:
            resp = await client.put(
                f"/collections/{self._collection}/points",
                params={"wait": "true"},
                json={"points": points},
            )
        resp.raise_for_status()

    async def aclose(self) -> None:
        # Tidak ada client persisten — client dibuat & ditutup per-panggilan.
        return None


_retriever: RAGRetriever | None = None
_retriever_lock = asyncio.Lock()


async def get_rag_retriever() -> RAGRetriever:
    """Return the process-wide RAGRetriever, calling ensure_collection only once."""
    global _retriever
    if _retriever is not None:
        return _retriever
    async with _retriever_lock:
        if _retriever is None:
            r = RAGRetriever()
            await r.ensure_collection()
            _retriever = r
    return _retriever
