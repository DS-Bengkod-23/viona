from __future__ import annotations

import structlog
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext

from app.core.config import settings
from app.domain.session import CustomerSessionData, PersonaKey
from app.infrastructure.metrics.prometheus import escalations_total, rag_queries_total
from app.infrastructure.session.store import get_session_store
from app.prompts.indonesian import (
    HUMAN_HANDOFF_ANNOUNCEMENT,
    build_rag_context,
    build_support_prompt,
)
from app.telephony.sip import transfer_to_human_agent

logger = structlog.get_logger(__name__)

RunCtx = RunContext[CustomerSessionData]


class BaseVionaAgent(Agent):
    async def on_enter(self) -> None:
        logger.info("agent enter", agent=type(self).__name__)
        userdata: CustomerSessionData = self.session.userdata

        chat_ctx = self.chat_ctx.copy()
        prev_agent = userdata.personas.get(PersonaKey.PREV)
        if prev_agent and prev_agent is not self:
            items = self._recent_items(prev_agent.chat_ctx.items)
            existing_ids = {item.id for item in chat_ctx.items}
            chat_ctx.items.extend(item for item in items if item.id not in existing_ids)

        chat_ctx.add_message(
            role="system",
            content=(
                f"Sesi ID: {userdata.session_id}. "
                f"Nama pelanggan: {userdata.customer_name or 'tidak diketahui'}."
            ),
        )
        await self.update_chat_ctx(chat_ctx)
        self.session.generate_reply()

    def _recent_items(self, items: list, n: int = 8) -> list:
        return [
            item for item in items
            if getattr(item, "role", None) != "system"
            and getattr(item, "type", None) not in ("function_call", "function_call_output")
        ][-n:]


class CustomerSupportAgent(BaseVionaAgent):
    def __init__(self) -> None:
        super().__init__(instructions=build_support_prompt(), allow_interruptions=True)

    async def on_enter(self) -> None:
        await super().on_enter()
        userdata: CustomerSessionData = self.session.userdata
        store = await get_session_store()
        await store.update(
            userdata.session_id,
            {
                "session_id": userdata.session_id,
                "customer_phone": userdata.customer_phone,
                "status": "active",
            },
        )

    @function_tool
    async def search_faq(self, context: RunCtx, query: str) -> str:
        """Cari informasi relevan dari basis pengetahuan untuk menjawab pertanyaan pelanggan.

        Args:
            query: Pertanyaan atau topik yang dicari dalam Bahasa Indonesia.
        """
        userdata = context.userdata
        if userdata.retriever is None:
            return "Maaf, basis pengetahuan tidak tersedia saat ini."

        rag_queries_total.labels(collection=settings.qdrant_collection).inc()
        results = await userdata.retriever.search(query, top_k=4, score_threshold=0.55)
        if not results:
            return "Tidak ada informasi relevan ditemukan untuk pertanyaan ini."
        return build_rag_context(results)

    @function_tool
    async def get_customer_info(self, context: RunCtx) -> str:
        """Ambil informasi sesi pelanggan saat ini dari memori."""
        userdata = context.userdata
        store = await get_session_store()
        data = await store.get(userdata.session_id)
        if not data:
            return "Tidak ada data pelanggan yang tersimpan untuk sesi ini."

        lines = [f"Session ID: {userdata.session_id}"]
        if data.get("customer_phone"):
            lines.append(f"Nomor telepon: {data['customer_phone']}")
        if data.get("customer_name"):
            lines.append(f"Nama: {data['customer_name']}")
        if data.get("complaints"):
            lines.append(f"Keluhan sebelumnya: {len(data['complaints'])} item")
        return "\n".join(lines)

    @function_tool
    async def save_customer_name(self, context: RunCtx, name: str) -> str:
        """Simpan nama pelanggan ke memori sesi.

        Args:
            name: Nama pelanggan yang disebutkan dalam percakapan.
        """
        userdata = context.userdata
        userdata.customer_name = name
        store = await get_session_store()
        await store.update(userdata.session_id, {"customer_name": name})
        logger.info("customer name saved", name=name, session=userdata.session_id)
        return f"Nama pelanggan '{name}' sudah dicatat."

    @function_tool
    async def file_complaint(
        self,
        context: RunCtx,
        description: str,
        category: str = "umum",
    ) -> str:
        """Catat keluhan pelanggan ke sistem.

        Args:
            description: Deskripsi keluhan pelanggan.
            category: Kategori keluhan (contoh: 'tagihan', 'produk', 'pengiriman', 'umum').
        """
        userdata = context.userdata
        userdata.complaint_count += 1
        ticket_id = f"TKT-{userdata.session_id[:8].upper()}-{userdata.complaint_count:03d}"

        store = await get_session_store()
        data = await store.get(userdata.session_id)
        complaints: list = data.get("complaints", [])
        complaints.append(
            {
                "ticket_id": ticket_id,
                "description": description,
                "category": category,
                "status": "open",
            }
        )
        await store.set(
            userdata.session_id,
            {**data, "complaints": complaints},
        )
        logger.info("complaint filed", ticket_id=ticket_id, category=category, session=userdata.session_id)
        return (
            f"Keluhan sudah dicatat. Nomor tiket kak: {ticket_id}. "
            "Tim kami akan menindaklanjuti dalam 1x24 jam."
        )

    @function_tool
    async def escalate_to_human(
        self,
        context: RunCtx,
        reason: str = "permintaan pelanggan",
    ) -> Agent:
        """Alihkan percakapan ke agen manusia jika masalah tidak dapat diselesaikan AI.

        Args:
            reason: Alasan eskalasi.
        """
        userdata = context.userdata
        userdata.escalated = True
        escalations_total.labels(reason=reason).inc()

        store = await get_session_store()
        await store.update(userdata.session_id, {"escalated": True, "escalation_reason": reason})
        logger.info("escalating to human", reason=reason, session=userdata.session_id)

        await self.session.say(HUMAN_HANDOFF_ANNOUNCEMENT, allow_interruptions=False)
        userdata.personas[PersonaKey.PREV] = self
        return userdata.personas[PersonaKey.ESCALATION]
