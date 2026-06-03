"""LiveKit Agent Worker entrypoint for Viona Voice AI."""
from __future__ import annotations

import asyncio

import httpx
import structlog
from livekit.agents import JobContext, RoomInputOptions, TurnHandlingOptions, WorkerOptions, cli
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
    # Sedikit lebih sensitif agar suara pelan / Bahasa Indonesia tetap terdeteksi;
    # silence yang lebih singkat → perpindahan ke STT lebih cepat setelah bicara.
    return silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=0.35,
        prefix_padding_duration=0.4,
        activation_threshold=0.35,
    )


def _build_stt() -> FasterWhisperSTT:
    """Return FasterWhisperSTT langsung.
    AgentSession auto-wraps non-streaming STT dengan StreamAdapter + VAD.

    Untuk testing:
      - WHISPER_MODEL_SIZE=small  (cepat, akurasi cukup untuk percakapan)
      - WHISPER_COMPUTE_TYPE=int8 (CPU-friendly, tidak butuh GPU)
      - beam_size=1               (lebih cepat, trade-off akurasi minimal)
    """
    return FasterWhisperSTT(
        model_size=settings.whisper_model_size,
        language=settings.whisper_language,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        vad_filter=False,
        beam_size=1,  # naikkan ke 3–5 untuk produksi
    )


def _build_llm() -> lk_openai.LLM:
    """Bangun LLM client.

    Untuk testing lokal gunakan model ringan:
      OLLAMA_MODEL=llama3.2:3b   (pull: docker compose exec ollama ollama pull llama3.2:3b)

    Untuk produksi:
      OLLAMA_MODEL=gpt-oss:120b-cloud
    """
    # Timeout lebih panjang untuk model Ollama yang besar / loading pertama kali
    return lk_openai.LLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key,
        temperature=0.7,           # lebih natural dari 0.5
        max_completion_tokens=256,  # pendek agar TTS cepat merespons
        timeout=httpx.Timeout(connect=30.0, read=180.0, write=60.0, pool=30.0),
    )


def _build_tts():
    """Bangun TTS (Text-to-Speech).

    Jika VOXCPM2_ENABLED=true, gunakan VoxCPM2 local TTS.
    Jika tidak, fallback ke Cartesia cloud TTS.

    VoxCPM2: Model TTS open-source yang berjalan secara lokal.
    Cartesia: Cloud TTS dengan suara Indonesia yang sudah dioptimalkan.
    """
    from app.infrastructure.tts.voxcpml2 import VoxCPML2TTS

    if settings.voxcpm2_enabled:
        logger.info("using VoxCPM2 TTS", model=settings.voxcpm2_model_name, device=settings.voxcpm2_device)
        return VoxCPML2TTS(
            model_name=settings.voxcpm2_model_name,
            device=settings.voxcpm2_device,
            voice_preset=settings.voxcpm2_voice_preset,
        )

    logger.info("using Cartesia TTS", voice_id=settings.cartesia_voice_id)
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
        stt=_build_stt(),
        llm=_build_llm(),
        tts=_build_tts(),
        # TurnHandlingOptions: gunakan dict nested (lihat docstring)
        turn_handling=TurnHandlingOptions(
            endpointing={"min_delay": 0.25, "max_delay": 1.25},
            interruption={"enabled": True},
        ),
    )

    @session.on("session_usage_updated")
    def _on_usage(usage) -> None:  # type: ignore[override]
        logger.debug("session usage updated", usage=str(usage))

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
            # RoomInputOptions masih tersedia di livekit-agents 1.5.x
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
