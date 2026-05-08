from __future__ import annotations

import structlog
from livekit.agents import JobContext
from livekit.protocol import sip as proto_sip

from app.core.config import settings

logger = structlog.get_logger(__name__)

_DEPARTMENT_ROUTES: dict[str, str] = {
    "umum":    "+6280011112222",
    "teknis":  "+6280011113333",
    "billing": "+6280011114444",
    "senior":  "+6280011115555",
}


async def transfer_to_human_agent(
    *,
    ctx: JobContext,
    department: str = "umum",
    session_id: str = "",
) -> bool:
    target_number = _DEPARTMENT_ROUTES.get(department, _DEPARTMENT_ROUTES["umum"])
    try:
        request = proto_sip.CreateSIPParticipantRequest(
            sip_trunk_id=settings.twilio_sip_trunk_sid,
            sip_call_to=target_number,
            room_name=ctx.room.name,
            participant_identity=f"human-agent-{department}",
            participant_name=f"Agen {department.capitalize()}",
            dtmf_digits="",
            play_ringtone=True,
        )
        await ctx.api.sip.create_sip_participant(request)
        logger.info(
            "sip transfer initiated",
            department=department,
            target=target_number,
            room=ctx.room.name,
            session=session_id,
        )
        return True
    except Exception as exc:
        logger.error(
            "sip transfer failed",
            department=department,
            error=str(exc),
            session=session_id,
        )
        return False


async def make_outbound_call(
    *,
    ctx: JobContext,
    phone_number: str,
) -> bool:
    try:
        request = proto_sip.CreateSIPParticipantRequest(
            sip_trunk_id=settings.twilio_sip_trunk_sid,
            sip_call_to=phone_number,
            room_name=ctx.room.name,
            participant_identity=f"outbound-{phone_number}",
            participant_name=phone_number,
            play_ringtone=True,
        )
        await ctx.api.sip.create_sip_participant(request)
        logger.info("outbound call initiated", target=phone_number, room=ctx.room.name)
        return True
    except Exception as exc:
        logger.error("outbound call failed", target=phone_number, error=str(exc))
        return False
