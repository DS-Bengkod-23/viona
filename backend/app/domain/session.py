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
    and the RAG retriever.
    """

    room_name: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    retriever: RAGRetriever | None = None
    lms_context: str = ""
