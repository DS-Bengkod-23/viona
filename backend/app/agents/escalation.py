from __future__ import annotations

import structlog
from livekit.agents.llm import function_tool

from app.agents.support import BaseVionaAgent, RunCtx
from app.infrastructure.session.store import get_session_store
from app.prompts.indonesian import ESCALATION_PROMPT
from app.telephony.sip import transfer_to_human_agent

logger = structlog.get_logger(__name__)


class HumanEscalationAgent(BaseVionaAgent):
    def __init__(self) -> None:
        super().__init__(instructions=ESCALATION_PROMPT, allow_interruptions=True)

    @function_tool
    async def connect_human_agent(
        self,
        context: RunCtx,
        department: str = "umum",
    ) -> str:
        """Sambungkan pelanggan ke agen manusia di departemen yang diminta.

        Args:
            department: Departemen tujuan ('umum', 'teknis', 'billing', 'senior').
        """
        userdata = context.userdata
        if userdata.ctx is None:
            return "Tidak dapat melakukan transfer – konteks ruangan tidak tersedia."

        logger.info("initiating human transfer", department=department, session=userdata.session_id)
        success = await transfer_to_human_agent(
            ctx=userdata.ctx,
            department=department,
            session_id=userdata.session_id,
        )

        if success:
            return "Transfer ke agen manusia berhasil. Pelanggan sedang dihubungkan."
        return (
            "Maaf kak, agen manusia sedang tidak tersedia saat ini. "
            "Kami akan menghubungi kembali dalam waktu dekat."
        )

    @function_tool
    async def take_callback_number(self, context: RunCtx, phone_number: str) -> str:
        """Catat nomor telepon untuk dihubungi kembali jika agen manusia tidak tersedia.

        Args:
            phone_number: Nomor telepon pelanggan dalam format internasional.
        """
        userdata = context.userdata
        store = await get_session_store()
        await store.update(
            userdata.session_id,
            {"callback_number": phone_number, "callback_requested": True},
        )
        logger.info("callback requested", phone=phone_number, session=userdata.session_id)
        return (
            f"Baik kak, nomor {phone_number} sudah kami catat. "
            "Agen kami akan menghubungi dalam 30 menit."
        )
