"""CLI script for bulk knowledge-base ingestion."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import structlog

from app.core.logging import configure_logging
from app.infrastructure.rag.ingestion import PDFIngester
from app.infrastructure.rag.retriever import RAGRetriever

logger = structlog.get_logger(__name__)


async def _run(paths: list[Path], category: str) -> None:
    retriever = RAGRetriever()
    ingester = PDFIngester(retriever)
    total = 0
    for path in paths:
        if path.suffix.lower() == ".pdf":
            n = await ingester.ingest_pdf(path, category=category)
        else:
            n = await ingester.ingest_text(path.read_text(), source=path.name, category=category)
        logger.info("ingested", file=str(path), chunks=n)
        total += n
    logger.info("done", total_chunks=total)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant knowledge base")
    parser.add_argument("files", nargs="+", type=Path, help="PDF or text files to ingest")
    parser.add_argument("--category", default="faq", help="Document category tag")
    args = parser.parse_args()
    asyncio.run(_run(args.files, args.category))


if __name__ == "__main__":
    main()
