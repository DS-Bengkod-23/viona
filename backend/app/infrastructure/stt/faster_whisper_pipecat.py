"""Faster-Whisper STT service for the Pipecat pipeline.

Wraps faster-whisper as a Pipecat ``SegmentedSTTService``: the pipeline's VAD
gates speech into segments, and each whole segment (16-bit mono PCM @ 16 kHz) is
transcribed in one batch call. Mirrors the structure of Pipecat's bundled
Whisper/Moonshine STT services.

The model-loading logic mirrors the original LiveKit plugin in
``app/infrastructure/stt/faster_whisper.py`` (which is retired with the
migration to Pipecat).
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import numpy as np
import structlog
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = structlog.get_logger(__name__)

WHISPER_SAMPLE_RATE = 16000


class FasterWhisperSTTService(SegmentedSTTService):
    """Transcribe VAD-segmented audio with a local faster-whisper model.

    Audio is expected as 16-bit signed mono PCM at 16 kHz (Pipecat's default
    input rate), so no resampling is needed inside the service.
    """

    def __init__(
        self,
        *,
        model_size: str = "large-v3",
        language: str = "id",
        device: str = "auto",
        compute_type: str = "float16",
        beam_size: int = 1,
        # Silero VAD upstream already sends speech-only chunks, so whisper's own
        # VAD filter tends to drop them -> empty transcripts. Keep it off.
        vad_filter: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(sample_rate=WHISPER_SAMPLE_RATE, **kwargs)
        self._model_size = model_size
        self._language = language
        self._device = device
        self._compute_type = compute_type
        self._beam_size = beam_size
        self._vad_filter = vad_filter
        self._model: WhisperModel | None = None
        self._model_lock = asyncio.Lock()
        self._frame_language = _resolve_language(language)

    def can_generate_metrics(self) -> bool:
        return True

    def _create_model(self) -> WhisperModel:
        from faster_whisper import WhisperModel

        logger.info(
            "loading faster-whisper model", model=self._model_size, device=self._device
        )
        model = WhisperModel(
            self._model_size, device=self._device, compute_type=self._compute_type
        )
        logger.info("faster-whisper model ready", model=self._model_size)
        return model

    async def _ensure_model(self) -> WhisperModel:
        async with self._model_lock:
            if self._model is None:
                self._model = await asyncio.to_thread(self._create_model)
            return self._model

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        """Transcribe one VAD-gated audio segment.

        Args:
            audio: Raw 16-bit signed mono PCM at 16 kHz.
        """
        model = await self._ensure_model()

        samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.size == 0:
            return

        await self.start_processing_metrics()

        def _transcribe() -> str:
            segments, _info = model.transcribe(
                samples,
                language=self._language,
                beam_size=self._beam_size,
                vad_filter=self._vad_filter,
                word_timestamps=False,
            )
            return " ".join(seg.text for seg in segments).strip()

        text = await asyncio.to_thread(_transcribe)

        await self.stop_processing_metrics()

        if text:
            logger.info("transcription done", preview=text[:120])
            yield TranscriptionFrame(
                text, self._user_id, time_now_iso8601(), self._frame_language
            )


def _resolve_language(language: str) -> Language | None:
    """Best-effort map an ISO code (e.g. 'id') to the Pipecat Language enum."""
    try:
        return Language(language)
    except ValueError:
        return getattr(Language, language.upper(), None)
