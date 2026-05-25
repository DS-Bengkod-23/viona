from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import numpy as np
import structlog

from livekit.agents.stt import STT, STTCapabilities, SpeechData, SpeechEvent, SpeechEventType
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, APIConnectOptions, NotGivenOr
from livekit.agents.utils import AudioBuffer

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = structlog.get_logger(__name__)

_TARGET_RATE = 16_000


def _frames_to_float32(buffer: AudioBuffer) -> np.ndarray:
    frames = buffer if isinstance(buffer, list) else [buffer]
    chunks: list[np.ndarray] = []

    for frame in frames:
        samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32) / 32768.0
        if frame.num_channels > 1:
            samples = samples.reshape(-1, frame.num_channels).mean(axis=1)
        if frame.sample_rate != _TARGET_RATE:
            import math
            new_len = math.ceil(len(samples) * _TARGET_RATE / frame.sample_rate)
            samples = np.interp(
                np.linspace(0, len(samples) - 1, new_len),
                np.arange(len(samples)),
                samples,
            ).astype(np.float32)
        chunks.append(samples)

    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)


class FasterWhisperSTT(STT):
    """Non-streaming STT backed by faster-whisper.

    Wrap with StreamAdapter + Silero VAD for use inside AgentSession.
    """

    def __init__(
        self,
        *,
        model_size: str = "large-v3",
        language: str = "id",
        device: str = "auto",
        compute_type: str = "float16",
        beam_size: int = 5,
        # Silero VAD + StreamAdapter already send speech-only chunks; whisper's
        # built-in VAD often drops those clips → empty transcripts / no LLM input.
        vad_filter: bool = False,
        num_workers: int = 1,
    ) -> None:
        super().__init__(capabilities=STTCapabilities(streaming=False, interim_results=False))
        self._model_size = model_size
        self._language = language
        self._device = device
        self._compute_type = compute_type
        self._beam_size = beam_size
        self._vad_filter = vad_filter
        self._executor = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="whisper")
        self._model: WhisperModel | None = None
        self._model_lock = asyncio.Lock()

    @property
    def model(self) -> str:
        return f"faster-whisper/{self._model_size}"

    @property
    def provider(self) -> str:
        return "faster-whisper"

    async def _load_model(self) -> WhisperModel:
        async with self._model_lock:
            if self._model is not None:
                return self._model
            logger.info("loading faster-whisper model", model=self._model_size, device=self._device)
            loop = asyncio.get_running_loop()
            self._model = await loop.run_in_executor(self._executor, self._create_model)
            logger.info("faster-whisper model ready", model=self._model_size)
            return self._model

    def _create_model(self) -> WhisperModel:
        from faster_whisper import WhisperModel
        return WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type)

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> SpeechEvent:
        model = await self._load_model()
        lang = language if language is not NOT_GIVEN and language else self._language
        audio = _frames_to_float32(buffer)

        if audio.size == 0:
            return SpeechEvent(
                type=SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[SpeechData(language=lang, text="")],
            )

        def _transcribe():
            segs, res_info = model.transcribe(
                audio,
                language=lang,
                beam_size=self._beam_size,
                vad_filter=self._vad_filter,
                word_timestamps=False,
            )
            # Evaluate generator inside thread to prevent blocking event loop
            return list(segs), res_info

        t0 = time.perf_counter()
        loop = asyncio.get_running_loop()
        segments, info = await loop.run_in_executor(self._executor, _transcribe)
        elapsed = time.perf_counter() - t0

        text = " ".join(seg.text for seg in segments).strip()
        confidence = float(np.exp(np.mean([seg.avg_logprob for seg in segments]))) if segments else 0.0

        dur_s = float(audio.size / _TARGET_RATE) if audio.size else 0.0
        if dur_s >= 0.15 and not text:
            logger.warning(
                "stt empty transcript on speech-length audio",
                seconds=round(dur_s, 2),
                lang=getattr(info, "language", None),
            )
        elif text:
            logger.info(
                "transcription done",
                lang=info.language,
                elapsed=round(elapsed, 3),
                audio_s=round(dur_s, 2),
                preview=text[:120],
            )
        else:
            logger.debug("stt no text (short clip)", seconds=round(dur_s, 3))

        return SpeechEvent(
            type=SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[SpeechData(language=info.language, text=text, confidence=min(confidence, 1.0))],
        )

    async def aclose(self) -> None:
        self._executor.shutdown(wait=False)
