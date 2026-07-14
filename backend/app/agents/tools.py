"""Tool handlers for the Viona voice agent.

Only ``search_faq`` remains — RAG is **parked** (the LMS pivot answers from injected
page context, not vector search), so this tool is not currently exposed on any flow
node but is kept for when/if RAG is re-wired. Customer-service handlers (customer
info, complaints, human escalation) were removed with the pivot.

Convention (pipecat-flows):

    async def handler(args: dict, flow_manager: FlowManager)
        -> tuple[result, next_node | None]

Shared per-call state lives in ``flow_manager.state["session"]`` as a ``VionaSession``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.core.config import settings
from app.domain.session import VionaSession
from app.infrastructure.metrics.prometheus import rag_queries_total
from app.prompts.indonesian import build_rag_context

if TYPE_CHECKING:
    from pipecat_flows import FlowManager

logger = structlog.get_logger(__name__)

ToolResult = tuple[Any, None]


def _session(flow_manager: FlowManager) -> VionaSession:
    return flow_manager.state["session"]


async def search_faq(args: dict, flow_manager: FlowManager) -> ToolResult:
    """Cari informasi relevan dari basis pengetahuan (RAG — parked)."""
    query = args["query"]
    session = _session(flow_manager)
    if session.retriever is None:
        return "Maaf, basis pengetahuan tidak tersedia saat ini.", None

    rag_queries_total.labels(collection=settings.qdrant_collection).inc()
    results = await session.retriever.search(query, top_k=4, score_threshold=0.55)
    if not results:
        return "Tidak ada informasi relevan ditemukan untuk pertanyaan ini.", None
    return build_rag_context(results), None
