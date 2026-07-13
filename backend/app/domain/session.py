from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.rag.retriever import RAGRetriever


@dataclass
class VionaSession:
    """Shared per-call state for the Pipecat pipeline.

    Stored in ``flow_manager.state["session"]`` so every tool handler can read
    and mutate it. Carries no LiveKit job/agent references — only the room name
    (for SIP transfer) and the RAG retriever.
    """

    room_name: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_name: str = ""
    customer_phone: str = ""
    complaint_count: int = 0
    escalated: bool = False
    retriever: RAGRetriever | None = None
    lms_context: str = ""
