"""LiveKit Agent Worker entrypoint for Viona Voice AI."""
from __future__ import annotations

import asyncio

import structlog
from livekit.agents import JobContext, RoomInputOptions, WorkerOptions, cli
from livekit.agents.stt import StreamAdapter
from livekit.agents.voice import AgentSession
from livekit.plugins import cartesia, noise_cancellation
from livekit.plugins import openai as lk_openai
from livekit.plugins import silero

from app.agents.escalation import HumanEscalationAgent
from app.agents.support import CustomerSupportAgent
from app.core.config import settings
from app.core.logging import configure_logging
from app.domain.session import CustomerSessionData, PersonaKey
from app.infrastructure.metrics.prometheus import active_sessions, agent_ready
from app.infrastructure.rag.retriever import get_rag_retriever
from app.infrastructure.session.store import get_session_store
from app.infrastructure.stt.faster_whisper import FasterWhisperSTT

logger = structlog.get_logger(__name__)


def _build_vad() -> silero.VAD:
    return silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=0.55,
        prefix_padding_duration=0.5,
        activation_threshold=0.5,
    )


def _build_stt(vad: silero.VAD) -> StreamAdapter:
    whisper = FasterWhisperSTT(
        model_size=settings.whisper_model_size,
        language=settings.whisper_language,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    return StreamAdapter(stt=whisper, vad_stream=vad.stream())


def _build_llm() -> lk_openai.LLM:
    return lk_openai.LLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key,
        temperature=0.5,
        max_tokens=512,
    )


def _build_tts() -> cartesia.TTS:
    return cartesia.TTS(
        model=settings.cartesia_model,
        voice=settings.cartesia_voice_id,
        language="id",
        api_key=settings.cartesia_api_key,
        encoding="pcm_s16le",
        sample_rate=24000,
    )


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    active_sessions.inc()
    participant = await ctx.wait_for_participant()
    phone = participant.identity if participant else ""

    logger.info("session started", room=ctx.room.name, participant=phone)

    retriever = await get_rag_retriever()

    userdata = CustomerSessionData(customer_phone=phone, ctx=ctx, retriever=retriever)

    support_agent = CustomerSupportAgent()
    escalation_agent = HumanEscalationAgent()
    userdata.personas[PersonaKey.SUPPORT] = support_agent
    userdata.personas[PersonaKey.ESCALATION] = escalation_agent

    vad = _build_vad()

    session: AgentSession[CustomerSessionData] = AgentSession(
        userdata=userdata,
        vad=vad,
        stt=_build_stt(vad),
        llm=_build_llm(),
        tts=_build_tts(),
        allow_interruptions=True,
        min_endpointing_delay=0.4,
        max_endpointing_delay=2.5,
    )

    @session.on("metrics_collected")
    def _on_metrics(metrics) -> None:  # type: ignore[override]
        logger.debug("pipeline metrics", metrics=str(metrics))

    @session.on("user_input_transcribed")
    def _on_transcript(event) -> None:  # type: ignore[override]
        transcript = getattr(event, "transcript", "")
        if not transcript:
            return

        async def _log() -> None:
            store = await get_session_store()
            await store.log_interaction(userdata.session_id, "user", transcript)

        def _on_done(task: asyncio.Task) -> None:
            if task.exception():
                logger.error("transcript log failed", error=str(task.exception()))

        asyncio.create_task(_log()).add_done_callback(_on_done)

    agent_ready.set(1)
    try:
        await session.start(
            agent=support_agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
        )
    finally:
        active_sessions.dec()
        agent_ready.set(0)

        store = await get_session_store()
        await store.update(userdata.session_id, {"status": "ended"})

        logger.info("session ended", session=userdata.session_id, room=ctx.room.name)


def main() -> None:
    configure_logging()
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="viona-customer-support",
        )
    )


if __name__ == "__main__":
    main()
