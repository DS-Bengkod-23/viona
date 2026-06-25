"""pipecat-flows definition for the Viona voice agent.

Two nodes mirror the old LiveKit multi-agent setup:

- ``support``    — the default customer-support persona + its tools.
- ``escalation`` — senior/escalation persona reached when ``escalate_to_human``
  fires; announces the handoff and exposes the human-transfer tools.

The handoff (``escalate_to_human``) returns the escalation node as the next
node, which is how pipecat-flows performs the transition (replacing the old
``Agent`` swap via ``PersonaKey.PREV``).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import structlog
from pipecat_flows import FlowsFunctionSchema, NodeConfig

from app.agents import tools
from app.infrastructure.metrics.prometheus import escalations_total
from app.infrastructure.session.store import get_session_store
from app.prompts.indonesian import (
    ESCALATION_PROMPT,
    HUMAN_HANDOFF_ANNOUNCEMENT,
    build_support_prompt,
)

if TYPE_CHECKING:
    from pipecat_flows import FlowManager

logger = structlog.get_logger(__name__)


def _fn(
    name: str,
    description: str,
    handler: Callable,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> FlowsFunctionSchema:
    return FlowsFunctionSchema(
        name=name,
        description=description,
        properties=properties or {},
        required=required or [],
        handler=handler,
    )


async def escalate_to_human(args: dict, flow_manager: FlowManager):
    """Transition support -> escalation node (the multi-agent handoff)."""
    reason = args.get("reason", "permintaan pelanggan")
    session = flow_manager.state["session"]
    session.escalated = True
    escalations_total.labels(reason=reason).inc()
    store = await get_session_store()
    await store.update(
        session.session_id, {"escalated": True, "escalation_reason": reason}
    )
    logger.info("escalating to human", reason=reason, session=session.session_id)
    return {"status": "escalated", "reason": reason}, create_escalation_node()


def create_support_node() -> NodeConfig:
    return {
        "name": "support",
        "role_message": build_support_prompt(),
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Sapa pelanggan dengan ramah dan bantu pertanyaan atau keluhan "
                    "mereka. Gunakan tools bila perlu."
                ),
            }
        ],
        "functions": [
            _fn(
                "search_faq",
                "Cari informasi relevan dari basis pengetahuan untuk menjawab "
                "pertanyaan pelanggan.",
                tools.search_faq,
                {
                    "query": {
                        "type": "string",
                        "description": "Pertanyaan atau topik dalam Bahasa Indonesia.",
                    }
                },
                ["query"],
            ),
            _fn(
                "get_customer_info",
                "Ambil informasi sesi pelanggan saat ini dari memori.",
                tools.get_customer_info,
            ),
            _fn(
                "save_customer_name",
                "Simpan nama pelanggan ke memori sesi.",
                tools.save_customer_name,
                {"name": {"type": "string", "description": "Nama pelanggan."}},
                ["name"],
            ),
            _fn(
                "file_complaint",
                "Catat keluhan pelanggan ke sistem.",
                tools.file_complaint,
                {
                    "description": {
                        "type": "string",
                        "description": "Deskripsi keluhan pelanggan.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Kategori: tagihan, produk, pengiriman, umum.",
                    },
                },
                ["description"],
            ),
            _fn(
                "escalate_to_human",
                "Alihkan percakapan ke agen manusia jika masalah tidak dapat "
                "diselesaikan AI.",
                escalate_to_human,
                {"reason": {"type": "string", "description": "Alasan eskalasi."}},
            ),
        ],
    }


def create_escalation_node() -> NodeConfig:
    return {
        "name": "escalation",
        "task_messages": [{"role": "system", "content": ESCALATION_PROMPT}],
        "pre_actions": [{"type": "tts_say", "text": HUMAN_HANDOFF_ANNOUNCEMENT}],
        "functions": [
            _fn(
                "connect_human_agent",
                "Sambungkan pelanggan ke agen manusia di departemen yang diminta.",
                tools.connect_human_agent,
                {
                    "department": {
                        "type": "string",
                        "description": "umum, teknis, billing, atau senior.",
                    }
                },
            ),
            _fn(
                "take_callback_number",
                "Catat nomor telepon untuk dihubungi kembali jika agen manusia "
                "tidak tersedia.",
                tools.take_callback_number,
                {
                    "phone_number": {
                        "type": "string",
                        "description": "Nomor telepon format internasional.",
                    }
                },
                ["phone_number"],
            ),
        ],
    }
