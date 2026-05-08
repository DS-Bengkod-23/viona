from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from livekit.agents import JobContext
    from livekit.agents.voice import Agent
    from app.infrastructure.rag.retriever import RAGRetriever


class PersonaKey(StrEnum):
    SUPPORT = "support"
    ESCALATION = "escalation"
    PREV = "_prev"


@dataclass
class CustomerSessionData:
    """Shared state across all agents in one voice session."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_name: str = ""
    customer_phone: str = ""
    complaint_count: int = 0
    escalated: bool = False
    personas: dict[str, Any] = field(default_factory=dict)
    ctx: JobContext | None = None
    retriever: RAGRetriever | None = None
