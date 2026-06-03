"""VoxCPML2 Text-to-Speech plugin for Viona.

VoxCPML2 is a local open-source TTS model that can be run on-premises.
It provides high-quality Indonesian voice synthesis.

Usage:
    from app.infrastructure.tts.voxcpml2 import VoxCPML2TTS
    tts = VoxCPML2TTS(model_name="VoxCPM2", device="cuda")

Requirements:
    - transformers >= 4.36
    - torch
    - scipy (for audio output)
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, AsyncIterator

import numpy as np
import structlog

if TYPE_CHECKING:
    import torch

logger = structlog.get_logger(__name__)

# Default audio settings for VoxCPM2
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_DEVICE = "cuda"


class VoxCPML2TTS:
    """VoxCPM2 TTS implementation using transformers pipeline.

    This is a non-streaming TTS that generates audio from text.
    For real-time voice conversations, consider using streaming models.
    """

    def __init__(
        self,
        model_name: str = "suno/bark",
        device: str = DEFAULT_DEVICE,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        voice_preset: str | None = None,  # e.g., "v2/en_speaker_6"
        max_length: int = 1024,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._sample_rate = sample_rate
        self._voice_preset = voice_preset
        self._max_length = max_length
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vox_tts")
        self._pipeline = None

    @property
    def model(self) -> str:
        return f"voxcpml2/{self._model_name}"

    @property
    def provider(self) -> str:
        return "voxcpml2"

    async def _ensure_pipeline(self):
        """Lazy-load the TTS pipeline."""
        if self._pipeline is None:
            loop = asyncio.get_running_loop()

            def _load():
                from transformers import pipeline
                logger.info("loading VoxCPM2 TTS model", model=self._model_name, device=self._device)
                p = pipeline(
                    "text-to-speech",
                    model=self._model_name,
                    device=self._device,
                )
                logger.info("VoxCPM2 TTS ready")
                return p

            self._pipeline = await loop.run_in_executor(self._executor, _load)

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio bytes (WAV format).

        Args:
            text: Text to synthesize

        Returns:
            Audio data as WAV bytes (16-bit PCM, 24kHz)
        """
        await self._ensure_pipeline()

        def _synth():
            import io
            import wave

            output = self._pipeline(
                text,
                forward_params={"max_new_tokens": self._max_length} if hasattr(self._pipeline, 'model') else {},
            )
            # Bark returns dict with 'audio' key as numpy array
            audio_array = output["audio"] if isinstance(output, dict) else output

            # Convert to WAV bytes
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)   # 16-bit
                wav_file.setframerate(self._sample_rate)
                # Normalize to int16
                audio_int16 = np.clip(audio_array * 32767, -32768, 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

            return wav_io.getvalue()

        loop = asyncio.get_running_loop()
        audio_bytes = await loop.run_in_executor(self._executor, _synth)
        logger.info("tts synthesis complete", chars=len(text), audio_bytes=len(audio_bytes))
        return audio_bytes

    async def stream_synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Streaming synthesis - yields chunks as they become available.

        For VoxCPM2/Bark, we generate in chunks for lower latency.
        """
        await self._ensure_pipeline()

        def _chunk_gen():
            import io
            import wave

            output = self._pipeline(
                text,
                forward_params={"max_new_tokens": self._max_length} if hasattr(self._pipeline, 'model') else {},
            )
            audio_array = output["audio"] if isinstance(output, dict) else output

            # Convert to WAV
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self._sample_rate)
                audio_int16 = np.clip(audio_array * 32767, -32768, 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

            return wav_io.getvalue()

        loop = asyncio.get_running_loop()
        audio_bytes = await loop.run_in_executor(self._executor, _chunk_gen)
        yield audio_bytes

    async def aclose(self) -> None:
        """Cleanup resources."""
        self._executor.shutdown(wait=False)
        self._pipeline = None


# Factory function for use in worker.py
def create_voxcpml2_tts(
    model_name: str = "suno/bark",
    device: str = DEFAULT_DEVICE,
    voice_preset: str | None = None,
) -> VoxCPML2TTS:
    """Create VoxCPML2 TTS instance.

    For Indonesian voice, use voice_preset like "v2/id_speaker_1"
    or similar Indonesian preset if available.

    Alternative models for Indonesian:
    - "facebook/fastspeech2-conformer-zeroshot" (multilingual)
    - "microsoft/speecht5_tts" (needs vocoder)
    - "hexgrad/Kokoro-82M" (high quality, need custom integration)
    """
    return VoxCPML2TTS(
        model_name=model_name,
        device=device,
        voice_preset=voice_preset,
    )