"""VoxCPM2 Text-to-Speech service for the Pipecat pipeline.

Wraps the local VoxCPM2 model (with zero-shot voice cloning) as a Pipecat
``TTSService``. Pipecat aggregates the LLM output into full sentences before
calling ``run_tts``, so the LaTeX/math cleaner (``normalize_for_tts``) sees
whole sentences and never a mid-expression fragment.

Synthesis logic mirrors the original LiveKit plugin in
``app/infrastructure/tts/voxcpml2.py`` (retired with the Pipecat migration) but
is standalone here so it carries no livekit-agents dependency.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path

import numpy as np
import structlog
from pipecat.audio.utils import create_stream_resampler
from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame
from pipecat.services.tts_service import TTSService

from app.core.text_cleaner import normalize_for_tts

logger = structlog.get_logger(__name__)

# VoxCPM2 emits 24 kHz mono float audio.
VOX_NATIVE_RATE = 24000

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "assets"
DEFAULT_REFERENCE_AUDIO = ASSETS_DIR / "voice_reference_processed.wav"
DEFAULT_REFERENCE_META = ASSETS_DIR / "voice_reference.json"


class VoxCPML2TTSService(TTSService):
    """Local VoxCPM2 TTS with voice cloning, as a Pipecat service."""

    def __init__(
        self,
        *,
        model_name: str = "openbmb/VoxCPM2",
        device: str = "cuda",
        sample_rate: int = VOX_NATIVE_RATE,
        voice_preset: str | None = None,
        reference_audio_path: str | None = None,
        reference_transcript: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._model_name = model_name
        self._device = device
        self._voice_preset = voice_preset
        self._model = None
        self._model_lock = asyncio.Lock()
        self._resampler = create_stream_resampler()

        self._reference_audio_path = self._resolve_reference_audio(reference_audio_path)
        self._reference_transcript = reference_transcript or self._load_transcript()

        cloning_mode = "ultimate" if self._reference_transcript else "controllable"
        logger.info(
            "VoxCPM2 TTS service initialized",
            model=model_name,
            device=device,
            cloning_mode=cloning_mode,
            reference_audio=str(self._reference_audio_path) if self._reference_audio_path else None,
        )

    def can_generate_metrics(self) -> bool:
        return True

    # ── reference audio / transcript resolution ─────────────────────────────
    def _resolve_reference_audio(self, path: str | None) -> Path | None:
        if path and Path(path).exists():
            return Path(path)
        if path:
            logger.warning("specified reference audio not found", path=path)
        if DEFAULT_REFERENCE_AUDIO.exists():
            return DEFAULT_REFERENCE_AUDIO
        logger.warning("no reference audio found, voice cloning disabled")
        return None

    def _load_transcript(self) -> str:
        if DEFAULT_REFERENCE_META.exists():
            try:
                meta = json.loads(DEFAULT_REFERENCE_META.read_text(encoding="utf-8"))
                return meta.get("transcript", "")
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("failed to load transcript metadata", error=str(exc))
        return ""

    # ── model loading ───────────────────────────────────────────────────────
    def _load_model(self):
        logger.info("loading VoxCPM2 model", model=self._model_name, device=self._device)
        try:
            from voxcpm import VoxCPM

            return {"type": "voxcpm", "model": VoxCPM.from_pretrained(self._model_name)}
        except ImportError:
            from transformers import pipeline

            p = pipeline("text-to-speech", model=self._model_name, device=self._device)
            return {"type": "pipeline", "model": p}

    async def _ensure_model(self):
        async with self._model_lock:
            if self._model is None:
                self._model = await asyncio.to_thread(self._load_model)
            return self._model

    def _synthesize(self, text: str) -> bytes:
        """Run blocking synthesis; return 16-bit mono PCM at VOX_NATIVE_RATE."""
        info = self._model
        model = info["model"]
        if info["type"] == "voxcpm":
            ref = self._reference_audio_path
            if ref and ref.exists():
                kwargs = {"text": text, "prompt_audio": str(ref)}
                if self._reference_transcript:
                    kwargs["prompt_text"] = self._reference_transcript
                wav = model.generate(**kwargs)
            else:
                wav = model.generate(text=text)
        else:
            forward = {"speaker_embeddings": self._voice_preset} if self._voice_preset else {}
            out = model(text, forward_params=forward)
            wav = out["audio"] if isinstance(out, dict) else out
        return _wav_to_pcm_bytes(wav)

    # ── Pipecat entrypoint ──────────────────────────────────────────────────
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame | None, None]:
        # Clean LaTeX/math + normalize for natural Indonesian speech.
        text = normalize_for_tts(text)
        if not text:
            return

        logger.debug("voxcpm synthesizing", chars=len(text))
        try:
            await self._ensure_model()
            await self.start_tts_usage_metrics(text)

            pcm = await asyncio.to_thread(self._synthesize, text)
            await self.stop_ttfb_metrics()

            # sample_rate is 0 until the pipeline sends a StartFrame; treat an
            # unset/native rate as VoxCPM's native 24 kHz (no resample).
            out_rate = self.sample_rate or VOX_NATIVE_RATE
            if out_rate != VOX_NATIVE_RATE:
                pcm = await self._resampler.resample(pcm, VOX_NATIVE_RATE, out_rate)

            # ~200 ms chunks for responsive playback / interruption.
            bytes_per_chunk = int(out_rate * 0.2) * 2  # 16-bit mono
            for offset in range(0, len(pcm), bytes_per_chunk):
                chunk = pcm[offset : offset + bytes_per_chunk]
                if not chunk:
                    break
                yield TTSAudioRawFrame(
                    audio=chunk,
                    sample_rate=out_rate,
                    num_channels=1,
                    context_id=context_id,
                )
        except Exception as exc:  # noqa: BLE001 - surface as pipeline error frame
            logger.error("voxcpm synthesis failed", error=str(exc))
            yield ErrorFrame(error=f"VoxCPM2 TTS error: {exc}")
        finally:
            await self.stop_ttfb_metrics()


def _wav_to_pcm_bytes(wav) -> bytes:
    """Convert model output (numpy/torch float) to 16-bit PCM LE bytes."""
    if isinstance(wav, np.ndarray):
        audio = wav
    elif hasattr(wav, "cpu"):
        audio = wav.cpu().numpy()
    else:
        audio = np.array(wav)
    if audio.ndim > 1:
        audio = audio.squeeze()
    return np.clip(audio * 32767, -32768, 32767).astype(np.int16).tobytes()
