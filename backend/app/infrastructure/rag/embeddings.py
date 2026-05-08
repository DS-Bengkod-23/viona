from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Sequence

import structlog

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 1024  # bge-m3 output dimension
_MODEL_NAME = "BAAI/bge-m3"
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embed")


@lru_cache(maxsize=1)
def _get_model():
    from fastembed import TextEmbedding
    logger.info("loading bge-m3 embedding model")
    model = TextEmbedding(model_name=_MODEL_NAME)
    logger.info("bge-m3 ready")
    return model


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    loop = asyncio.get_running_loop()

    def _run() -> list[list[float]]:
        return [v.tolist() for v in _get_model().embed(list(texts))]

    return await loop.run_in_executor(_EXECUTOR, _run)


async def embed_query(text: str) -> list[float]:
    results = await embed_texts([text])
    return results[0]
