from __future__ import annotations

import asyncio

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.infrastructure.rag.embeddings import EMBEDDING_DIM, embed_query

logger = structlog.get_logger(__name__)


class RAGRetriever:
    """Semantic retriever backed by Qdrant + bge-m3 embeddings."""

    def __init__(self) -> None:
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=10,
        )
        self._collection = settings.qdrant_collection

    async def ensure_collection(self) -> None:
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info("qdrant collection created", collection=self._collection)

    async def search(
        self,
        query: str,
        *,
        material_id: str | None = None,
        version: str | None = None,
        top_k: int = 4,
        score_threshold: float = 0.60,
    ) -> list[dict]:
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        vector = await embed_query(query)

        # Bangun filter pencarian Qdrant
        conditions = []
        if material_id:
            conditions.append(FieldCondition(key="material_id", match=MatchValue(value=material_id)))
        if version:
            conditions.append(FieldCondition(key="version", match=MatchValue(value=version)))

        qdrant_filter = Filter(must=conditions) if conditions else None

        hits = await self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            query_filter=qdrant_filter,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )

        results: list[dict] = []
        seen: set[str] = set()
        for hit in hits:
            text: str = hit.payload.get("text", "")
            if text in seen:
                continue
            seen.add(text)
            results.append({
                "id": str(hit.id),
                "score": round(hit.score, 4),
                "text": text,
                "source": hit.payload.get("source", ""),
                "category": hit.payload.get("category", ""),
            })

        logger.debug("rag search", query=query[:60], hits=len(results))
        return results

    async def upsert(self, points: list[dict]) -> None:
        structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in points
        ]
        await self._client.upsert(collection_name=self._collection, points=structs)

    async def aclose(self) -> None:
        await self._client.close()


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
