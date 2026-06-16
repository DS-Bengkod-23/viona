"""LiveKit Agent Worker entrypoint for Viona Voice AI."""
from __future__ import annotations

import asyncio

import httpx
import structlog
from livekit.agents import JobContext, RoomInputOptions, TurnHandlingOptions, WorkerOptions, cli
from livekit.agents.voice import AgentSession
from livekit.plugins import noise_cancellation
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
        min_silence_duration=0.2,
        prefix_padding_duration=0.4,
        activation_threshold=0.1,
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
        vad_filter=True,
        beam_size=1,  # turunkan ke 1 untuk streaming real-time yang lebih responsif
    )


def _build_llm() -> lk_openai.LLM:
    """Bangun LLM client.

    Untuk testing lokal gunakan model ringan:
      OLLAMA_MODEL=llama3.2:3b   (pull: docker compose exec ollama ollama pull llama3.2:3b)

    Untuk produksi:
      OLLAMA_MODEL=qwen3.5-cloud
    """
    # lk_openai.LLM wraps OpenAI SDK → membutuhkan /v1 endpoint.
    # settings.ollama_base_url sengaja TIDAK menyertakan /v1 agar chat.py dan
    # embeddings.py yang memakai native Ollama API (/api/generate, /api/embed)
    # tetap benar. Maka /v1 di-append hanya di sini.
    openai_compat_url = f"{settings.ollama_base_url.rstrip('/')}/v1"
    return lk_openai.LLM(
        model=settings.ollama_model,
        base_url=openai_compat_url,
        api_key=settings.ollama_api_key,
        temperature=0.7,           # lebih natural dari 0.5
        max_completion_tokens=256,  # pendek agar TTS cepat merespons
        timeout=httpx.Timeout(connect=30.0, read=180.0, write=60.0, pool=30.0),
        extra_body={"think": False},
    )


def _build_tts():
    """Bangun TTS (Text-to-Speech) menggunakan VoxCPM2 dengan voice cloning.

    VoxCPM2 mendukung zero-shot voice cloning: cukup berikan referensi audio
    dan model akan meng-clone timbre suara tersebut tanpa perlu training.

    Mode cloning:
    - Controllable: referensi audio saja (kualitas baik)
    - Ultimate: referensi audio + transcript (fidelitas terbaik)
    """
    from app.infrastructure.tts.voxcpml2 import VoxCPML2TTS

    logger.info(
        "using VoxCPM2 TTS with voice cloning",
        model=settings.voxcpm2_model_name,
        device=settings.voxcpm2_device,
        reference_audio=settings.voxcpm2_reference_audio,
    )
    return VoxCPML2TTS(
        model_name=settings.voxcpm2_model_name,
        device=settings.voxcpm2_device,
        voice_preset=settings.voxcpm2_voice_preset,
        reference_audio_path=settings.voxcpm2_reference_audio,
        reference_transcript=settings.voxcpm2_reference_transcript,
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
        # TurnHandlingOptions: dipercepat agar lebih responsif
        turn_handling=TurnHandlingOptions(
            endpointing={"min_delay": 0.1, "max_delay": 0.8},
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
