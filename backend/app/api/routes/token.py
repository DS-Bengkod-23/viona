from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from livekit.api import AccessToken, VideoGrants

from app.core.config import settings

router = APIRouter(prefix="/api", tags=["livekit"])


class TokenRequest(BaseModel):
    room: str = ""
    identity: str = ""
    lms_context: str = ""

@router.post("/token")
async def get_token(req: TokenRequest) -> dict:
    room = req.room
    identity = req.identity
    lms_context = req.lms_context

    if not room:
        room = f"support-{uuid.uuid4().hex[:8]}"
    if not identity:
        identity = f"customer-{uuid.uuid4().hex[:8]}"

    try:
        token = (
            AccessToken(
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            )
            .with_identity(identity)
            .with_name(identity)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .to_jwt()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {exc}") from exc

    import urllib.request
    import urllib.parse
    try:
        data = urllib.parse.urlencode({
            "room_name": room, 
            "identity": identity,
            "lms_context": lms_context
        }).encode('utf-8')
        req = urllib.request.Request("http://viona-agent:8081/dev/spawn", data=data)
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Failed to trigger dev spawn: {e}")

    return {
        "token": token,
        "room": room,
        "identity": identity,
        "livekit_url": settings.livekit_url,
    }
