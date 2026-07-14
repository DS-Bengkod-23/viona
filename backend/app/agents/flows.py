"""pipecat-flows definition for the Viona LMS learning companion.

Single node ``support``. Answers come from the LMS page content injected into the
persona prompt (``lms_context``) — a context-injection design that replaces RAG
for this domain. No tools are exposed: no RAG search (parked), no customer-service
handlers, no human escalation (all removed with the LMS pivot).
"""
from __future__ import annotations

from pipecat_flows import NodeConfig

from app.prompts.indonesian import build_support_prompt


def create_support_node(lms_context: str = "") -> NodeConfig:
    return {
        "name": "support",
        "role_message": build_support_prompt(lms_context=lms_context),
        "task_messages": [
            {
                "role": "system",
                "content": (
                    "Sapa siswa dengan ramah dan bantu mereka memahami materi yang "
                    "sedang dibaca. Jawab hanya seputar materi tersebut."
                ),
            }
        ],
        "functions": [],
    }
