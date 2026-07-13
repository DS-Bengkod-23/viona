"""pipecat-flows definition for the Viona voice agent.

Single node:

- ``support`` — the assistant persona + its tools.

Note: the customer-service escalation node (human handoff via Twilio SIP) was
removed with the pivot to the LMS learning-companion domain. The flow may later
be re-designed to distinguish an "explain" mode vs a strict "quiz" mode.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pipecat_flows import FlowsFunctionSchema, NodeConfig

from app.agents import tools
from app.prompts.indonesian import build_support_prompt


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


def create_support_node(lms_context: str = "") -> NodeConfig:
    return {
        "name": "support",
        "role_message": build_support_prompt(lms_context=lms_context),
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
        ],
    }
