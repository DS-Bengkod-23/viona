"""Tool handlers for the Pipecat voice agent.

These are the function-calling tools the LLM can invoke, ported from the
LiveKit ``@function_tool`` methods on ``CustomerSupportAgent`` /
``HumanEscalationAgent`` into plain async handlers that follow the
pipecat-flows convention:

    async def handler(args: dict, flow_manager: FlowManager)
        -> tuple[result, next_node | None]

Shared per-call state lives in ``flow_manager.state["session"]`` as a
``VionaSession``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.core.config import settings
from app.domain.session import VionaSession
from app.infrastructure.metrics.prometheus import rag_queries_total
from app.infrastructure.session.store import get_session_store
from app.prompts.indonesian import build_rag_context

if TYPE_CHECKING:
    from pipecat_flows import FlowManager

logger = structlog.get_logger(__name__)

ToolResult = tuple[Any, None]


def _session(flow_manager: FlowManager) -> VionaSession:
    return flow_manager.state["session"]


async def search_faq(args: dict, flow_manager: FlowManager) -> ToolResult:
    """Cari informasi relevan dari basis pengetahuan (RAG)."""
    query = args["query"]
    session = _session(flow_manager)
    if session.retriever is None:
        return "Maaf, basis pengetahuan tidak tersedia saat ini.", None

    rag_queries_total.labels(collection=settings.qdrant_collection).inc()
    results = await session.retriever.search(query, top_k=4, score_threshold=0.55)
    if not results:
        return "Tidak ada informasi relevan ditemukan untuk pertanyaan ini.", None
    return build_rag_context(results), None


async def get_customer_info(args: dict, flow_manager: FlowManager) -> ToolResult:
    """Ambil informasi sesi pelanggan saat ini dari memori."""
    session = _session(flow_manager)
    store = await get_session_store()
    data = await store.get(session.session_id)
    if not data:
        return "Tidak ada data pelanggan yang tersimpan untuk sesi ini.", None

    lines = [f"Session ID: {session.session_id}"]
    if data.get("customer_phone"):
        lines.append(f"Nomor telepon: {data['customer_phone']}")
    if data.get("customer_name"):
        lines.append(f"Nama: {data['customer_name']}")
    if data.get("complaints"):
        lines.append(f"Keluhan sebelumnya: {len(data['complaints'])} item")
    return "\n".join(lines), None


async def save_customer_name(args: dict, flow_manager: FlowManager) -> ToolResult:
    """Simpan nama pelanggan ke memori sesi."""
    name = args["name"]
    session = _session(flow_manager)
    session.customer_name = name
    store = await get_session_store()
    await store.update(session.session_id, {"customer_name": name})
    logger.info("customer name saved", name=name, session=session.session_id)
    return f"Nama pelanggan '{name}' sudah dicatat.", None
