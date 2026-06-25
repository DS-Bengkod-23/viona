"""Tool handlers for the Pipecat voice agent.

These are the function-calling tools the LLM can invoke, ported from the
LiveKit ``@function_tool`` methods on ``CustomerSupportAgent`` /
``HumanEscalationAgent`` into plain async handlers that follow the
pipecat-flows convention:

    async def handler(args: dict, flow_manager: FlowManager)
        -> tuple[result, next_node | None]

Shared per-call state lives in ``flow_manager.state["session"]`` as a
``VionaSession``. The node-transition tool (``escalate_to_human``) lives in
``flows.py`` since it needs the target node.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.core.config import settings
from app.domain.session import VionaSession
from app.infrastructure.metrics.prometheus import rag_queries_total
from app.infrastructure.session.store import get_session_store
from app.prompts.indonesian import build_rag_context
from app.telephony.sip import transfer_to_human_by_room

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


async def file_complaint(args: dict, flow_manager: FlowManager) -> ToolResult:
    """Catat keluhan pelanggan ke sistem."""
    description = args["description"]
    category = args.get("category", "umum")
    session = _session(flow_manager)
    session.complaint_count += 1
    ticket_id = f"TKT-{session.session_id[:8].upper()}-{session.complaint_count:03d}"

    store = await get_session_store()
    data = await store.get(session.session_id)
    complaints: list = data.get("complaints", [])
    complaints.append(
        {
            "ticket_id": ticket_id,
            "description": description,
            "category": category,
            "status": "open",
        }
    )
    await store.set(session.session_id, {**data, "complaints": complaints})
    logger.info(
        "complaint filed", ticket_id=ticket_id, category=category, session=session.session_id
    )
    return (
        f"Keluhan sudah dicatat. Nomor tiket kak: {ticket_id}. "
        "Tim kami akan menindaklanjuti dalam 1x24 jam.",
        None,
    )


async def connect_human_agent(args: dict, flow_manager: FlowManager) -> ToolResult:
    """Sambungkan pelanggan ke agen manusia via Twilio SIP transfer."""
    department = args.get("department", "umum")
    session = _session(flow_manager)
    logger.info(
        "initiating human transfer", department=department, session=session.session_id
    )
    success = await transfer_to_human_by_room(
        room_name=session.room_name,
        department=department,
        session_id=session.session_id,
    )
    if success:
        return "Transfer ke agen manusia berhasil. Pelanggan sedang dihubungkan.", None
    return (
        "Maaf kak, agen manusia sedang tidak tersedia saat ini. "
        "Kami akan menghubungi kembali dalam waktu dekat.",
        None,
    )


async def take_callback_number(args: dict, flow_manager: FlowManager) -> ToolResult:
    """Catat nomor telepon untuk dihubungi kembali."""
    phone_number = args["phone_number"]
    session = _session(flow_manager)
    store = await get_session_store()
    await store.update(
        session.session_id,
        {"callback_number": phone_number, "callback_requested": True},
    )
    logger.info("callback requested", phone=phone_number, session=session.session_id)
    return (
        f"Baik kak, nomor {phone_number} sudah kami catat. "
        "Agen kami akan menghubungi dalam 30 menit.",
        None,
    )
