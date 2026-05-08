from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import urlencode

import structlog
from fastapi import APIRouter, Form, Header, HTTPException, Request
from fastapi.responses import Response

from app.core.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/telephony", tags=["telephony"])

_TWIML_DIAL_SIP = """\
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial callerId="{from_number}" timeout="30">
        <Sip>{sip_uri};transport=tcp</Sip>
    </Dial>
</Response>
"""

_TWIML_REJECT = """\
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="id-ID">Maaf, layanan tidak tersedia saat ini. Silakan coba lagi nanti.</Say>
</Response>
"""


def _verify_twilio_signature(auth_token: str, signature: str, url: str, params: dict) -> bool:
    s = url + urlencode(sorted(params.items()))
    expected = base64.b64encode(
        hmac.new(auth_token.encode(), s.encode(), hashlib.sha1).digest()
    ).decode()
    return hmac.compare_digest(expected, signature)


@router.post("/voice")
async def twilio_voice(
    request: Request,
    x_twilio_signature: str = Header(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
    CallSid: str = Form(default=""),
) -> Response:
    if settings.twilio_auth_token:
        form_data = dict(await request.form())
        if not _verify_twilio_signature(
            settings.twilio_auth_token, x_twilio_signature, str(request.url), form_data
        ):
            logger.warning("twilio signature mismatch", call_sid=CallSid)
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    logger.info("inbound call", from_=From, to=To, call_sid=CallSid)
    livekit_sip_uri = settings.livekit_url.replace("wss://", "sip:").replace("https://", "sip:")
    return Response(
        content=_TWIML_DIAL_SIP.format(from_number=To, sip_uri=livekit_sip_uri),
        media_type="application/xml",
    )


@router.post("/status")
async def twilio_status(
    CallSid: str = Form(default=""),
    CallStatus: str = Form(default=""),
) -> dict:
    logger.info("call status", call_sid=CallSid, status=CallStatus)
    return {"received": True}
