from __future__ import annotations

import structlog
from livekit import api
from livekit.protocol import sip as proto_sip

from app.core.config import settings

logger = structlog.get_logger(__name__)

_DEPARTMENT_ROUTES: dict[str, str] = {
    "umum":    "+6280011112222",
    "teknis":  "+6280011113333",
    "billing": "+6280011114444",
    "senior":  "+6280011115555",
}


async def transfer_to_human_by_room(
    *,
    room_name: str,
    department: str = "umum",
    session_id: str = "",
) -> bool:
    """Transfer the call to a human agent using only the room name.

    Pipecat has no LiveKit ``JobContext``, so we create a short-lived
    ``LiveKitAPI`` client from settings instead of reusing ``ctx.api``.
    """
    target_number = _DEPARTMENT_ROUTES.get(department, _DEPARTMENT_ROUTES["umum"])
    lkapi = api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    try:
        request = proto_sip.CreateSIPParticipantRequest(
            sip_trunk_id=settings.twilio_sip_trunk_sid,
            sip_call_to=target_number,
            room_name=room_name,
            participant_identity=f"human-agent-{department}",
            participant_name=f"Agen {department.capitalize()}",
            dtmf_digits="",
            play_ringtone=True,
        )
        await lkapi.sip.create_sip_participant(request)
        logger.info(
            "sip transfer initiated",
            department=department,
            target=target_number,
            room=room_name,
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
    finally:
        await lkapi.aclose()
