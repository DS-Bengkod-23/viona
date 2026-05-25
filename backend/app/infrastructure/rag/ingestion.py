from __future__ import annotations

import asyncio
import bisect
import hashlib
import re
import uuid
from pathlib import Path

import structlog

from app.infrastructure.rag.embeddings import embed_texts
from app.infrastructure.rag.retriever import RAGRetriever

logger = structlog.get_logger(__name__)

_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # O(n) boundary list built once so per-chunk boundary search is O(log n)
    boundaries = sorted(m.start() + 1 for m in re.finditer(r"\. ", text))

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            lo = start + chunk_size // 2
            idx = bisect.bisect_right(boundaries, end) - 1
            if idx >= 0 and boundaries[idx] > lo:
                end = boundaries[idx]
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break

    return chunks


class PDFIngester:
    def __init__(self, retriever: RAGRetriever) -> None:
        self._retriever = retriever

    async def ingest_pdf(self, path: Path, *, category: str = "faq", material_id: str | None = None, version: str | None = None) -> int:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return await self._ingest(text, source=path.name, category=category, material_id=material_id, version=version)

    async def ingest_text(self, text: str, *, source: str = "manual", category: str = "faq", material_id: str | None = None, version: str | None = None) -> int:
        return await self._ingest(text, source=source, category=category, material_id=material_id, version=version)

    async def _ingest(self, text: str, *, source: str, category: str, material_id: str | None = None, version: str | None = None) -> int:
        chunks = _chunk_text(text)
        if not chunks:
            logger.warning("no chunks extracted", source=source)
            return 0

        await self._retriever.ensure_collection()
        vectors = await embed_texts(chunks)

        points: list[dict] = []
        for chunk, vector in zip(chunks, vectors):
            chunk_id = hashlib.sha256(f"{source}:{chunk}".encode()).hexdigest()[:16]
            payload = {"text": chunk, "source": source, "category": category}
            if material_id:
                payload["material_id"] = material_id
            if version:
                payload["version"] = version

            points.append({
                "id": str(uuid.UUID(bytes=bytes.fromhex(chunk_id.ljust(32, "0")))),
                "vector": vector,
                "payload": payload,
            })

        batch_size = 64
        batches = [points[i:i + batch_size] for i in range(0, len(points), batch_size)]
        await asyncio.gather(*[self._retriever.upsert(b) for b in batches])

        logger.info("ingestion complete", source=source, chunks=len(chunks))
        return len(chunks)
