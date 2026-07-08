"""Pipecat voice pipeline + per-room runner for Viona.

Replaces the LiveKit Agents worker. There is no job dispatch: a bot is spawned
per room by the ``/webhooks/livekit`` handler, which calls
:func:`run_bot_for_room`. The bot joins the room via Pipecat's
``LiveKitTransport`` and runs the VAD -> STT -> LLM(+flows) -> TTS pipeline.
"""
from __future__ import annotations

import asyncio

import structlog
from livekit import api
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.transports.livekit.transport import LiveKitParams, LiveKitTransport
from pipecat_flows import FlowManager

from app.agents.flows import create_support_node
from app.core.config import settings
from app.domain.session import VionaSession
from app.infrastructure.metrics.prometheus import active_sessions, agent_ready
from app.infrastructure.rag.retriever import get_rag_retriever
from app.infrastructure.session.store import get_session_store
from app.infrastructure.stt.faster_whisper_pipecat import FasterWhisperSTTService
from app.infrastructure.tts.voxcpml2_pipecat import VoxCPML2TTSService

logger = structlog.get_logger(__name__)

BOT_IDENTITY = "viona-bot"

# In-flight rooms, so a duplicate webhook never spawns a second bot.
_active_rooms: set[str] = set()


def _build_bot_token(room_name: str) -> str:
    return (
        api.AccessToken(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        .with_identity(BOT_IDENTITY)
        .with_name("Viona")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )


def _build_stt() -> FasterWhisperSTTService:
    return FasterWhisperSTTService(
        model_size=settings.whisper_model_size,
        language=settings.whisper_language,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        beam_size=1,
    )


def _build_llm() -> OLLamaLLMService:
    base_url = f"{settings.ollama_base_url.rstrip('/')}/v1"
    return OLLamaLLMService(model=settings.ollama_model, base_url=base_url)


def _build_tts() -> VoxCPML2TTSService:
    # VOXCPM2_ENABLED gates the local TTS. It is disabled on dev (CPU/Mac) where
    # VoxCPM2 can't run; fail loudly with an actionable message instead of a cryptic
    # torchaudio/CUDA crash at first synthesis. See docs/ENV_PROFILES.md.
    if not settings.voxcpm2_enabled:
        raise RuntimeError(
            "VoxCPM2 TTS is disabled (VOXCPM2_ENABLED=false). The Pipecat voice "
            "pipeline requires a TTS engine — enable it on a GPU host (prod profile) "
            "or wire an alternative TTS before spawning a bot."
        )
    return VoxCPML2TTSService(
        model_name=settings.voxcpm2_model_name,
        device=settings.voxcpm2_device,
        voice_preset=settings.voxcpm2_voice_preset,
        reference_audio_path=settings.voxcpm2_reference_audio,
        reference_transcript=settings.voxcpm2_reference_transcript,
    )


class TranscriptLogger(FrameProcessor):
    """Log finalized user transcripts to the session store (fire-and-forget)."""

    def __init__(self, session: VionaSession) -> None:
        super().__init__()
        self._session = session

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and frame.text:
            asyncio.create_task(self._log(frame.text))
        await self.push_frame(frame, direction)

    async def _log(self, text: str) -> None:
        try:
            store = await get_session_store()
            await store.log_interaction(self._session.session_id, "user", text)
        except Exception as exc:  # noqa: BLE001
            logger.error("transcript log failed", error=str(exc))


async def run_bot_for_room(room_name: str, customer_phone: str = "") -> None:
    """Join ``room_name`` and run the voice pipeline until the call ends."""
    if room_name in _active_rooms:
        logger.info("bot already active for room, skipping", room=room_name)
        return
    _active_rooms.add(room_name)

    logger.info("starting pipecat bot", room=room_name)
    retriever = await get_rag_retriever()
    session = VionaSession(
        room_name=room_name, customer_phone=customer_phone, retriever=retriever
    )

    transport = LiveKitTransport(
        url=settings.livekit_url,
        token=_build_bot_token(room_name),
        room_name=room_name,
        params=LiveKitParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
        ),
    )

    stt = _build_stt()
    llm = _build_llm()
    tts = _build_tts()

    context = LLMContext()
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            TranscriptLogger(session),
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    flow_manager = FlowManager(llm=llm, context_aggregator=aggregators, worker=task)
    flow_manager.state["session"] = session

    @transport.event_handler("on_first_participant_joined")
    async def _on_join(_transport, participant) -> None:  # noqa: ANN001
        active_sessions.inc()
        store = await get_session_store()
        await store.update(
            session.session_id,
            {
                "session_id": session.session_id,
                "customer_phone": session.customer_phone,
                "status": "active",
            },
        )
        await flow_manager.initialize(create_support_node())

    @transport.event_handler("on_participant_disconnected")
    async def _on_left(_transport, participant) -> None:  # noqa: ANN001
        logger.info("participant left, ending", room=room_name)
        await task.cancel()

    agent_ready.set(1)
    runner = PipelineRunner(handle_sigint=False)
    try:
        await runner.run(task)
    finally:
        _active_rooms.discard(room_name)
        active_sessions.dec()
        agent_ready.set(0)
        store = await get_session_store()
        await store.update(session.session_id, {"status": "ended"})
        logger.info("pipecat bot ended", room=room_name, session=session.session_id)
