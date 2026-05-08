from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.infrastructure.metrics.prometheus import metrics_output

router = APIRouter(tags=["observability"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "viona-api"}


@router.get("/ready")
async def ready() -> dict:
    return {"status": "ready"}


@router.get("/metrics")
async def metrics() -> Response:
    body, content_type = metrics_output()
    return Response(content=body, media_type=content_type)
