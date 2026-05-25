from __future__ import annotations

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.infrastructure.rag.ingestion import PDFIngester
from app.infrastructure.rag.retriever import get_rag_retriever

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])


async def _get_ingester() -> PDFIngester:
    return PDFIngester(await get_rag_retriever())


class TextIngestRequest(BaseModel):
    text: str
    source: str = "api"
    category: str = "faq"
    material_id: str | None = None
    version: str | None = None


@router.post("/pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    category: str = Form(default="faq"),
    material_id: str | None = Form(default=None),
    version: str | None = Form(default=None),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    import tempfile
    from pathlib import Path

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        chunks = await (await _get_ingester()).ingest_pdf(tmp_path, category=category, material_id=material_id, version=version)
        logger.info("pdf ingested", filename=file.filename, chunks=chunks, material_id=material_id, version=version)
        return {"filename": file.filename, "chunks": chunks, "status": "ok"}
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/text")
async def ingest_text(body: TextIngestRequest) -> dict:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")

    chunks = await (await _get_ingester()).ingest_text(
        body.text,
        source=body.source,
        category=body.category,
        material_id=body.material_id,
        version=body.version,
    )
    return {"source": body.source, "chunks": chunks, "status": "ok"}
