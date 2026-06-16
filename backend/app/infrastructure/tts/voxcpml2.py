"""VoxCPM2 Text-to-Speech plugin for Viona with Voice Cloning support.

VoxCPM2 is a local open-source TTS model that supports:
- Standard TTS synthesis
- Zero-shot voice cloning via reference audio
- Ultimate Cloning mode (reference audio + transcript) for highest fidelity

The model clones the voice timbre from a reference audio file without
requiring any fine-tuning or training.

Designed to be fully compatible with LiveKit Agents SDK 1.5.x:
- Extends tts.TTS and tts.ChunkedStream properly
- Uses rtc.AudioFrame for audio output (not raw bytes)
- Follows the initialize → push → flush pattern via AudioEmitter
"""
from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import structlog
from livekit import rtc
from livekit.agents import tts
from livekit.agents.utils import shortuuid

if TYPE_CHECKING:
    import torch

logger = structlog.get_logger(__name__)

# Default audio settings for VoxCPM2
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_NUM_CHANNELS = 1
DEFAULT_DEVICE = "cuda"
# PCM 16-bit = 2 bytes per sample
BYTES_PER_SAMPLE = 2

# Default reference audio paths (relative to backend/)
ASSETS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "assets"
DEFAULT_REFERENCE_AUDIO = ASSETS_DIR / "voice_reference_processed.wav"
DEFAULT_REFERENCE_META = ASSETS_DIR / "voice_reference.json"


class VoxCPML2TTS(tts.TTS):
    """VoxCPM2 TTS with zero-shot voice cloning, integrated with LiveKit Agents.

    Fully compatible with LiveKit Agents SDK 1.5.x:
    - Implements synthesize() → ChunkedStream pattern
    - Uses rtc.AudioFrame for audio output
    - Follows AudioEmitter initialize → push → flush lifecycle

    Supports two cloning modes:
    - Controllable Cloning: reference audio only (good quality)
    - Ultimate Cloning: reference audio + transcript (best fidelity)
    """

    def __init__(
        self,
        model_name: str = "openbmb/VoxCPM2",
        device: str = DEFAULT_DEVICE,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        num_channels: int = DEFAULT_NUM_CHANNELS,
        voice_preset: str | None = None,
        reference_audio_path: str | None = None,
        reference_transcript: str | None = None,
        max_length: int = 1024,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,
                aligned_transcript=False,
            ),
            sample_rate=sample_rate,
            num_channels=num_channels,
        )
        self._model_name = model_name
        self._device = device
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._voice_preset = voice_preset
        self._max_length = max_length
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vox_tts")
        self._model = None

        # Voice cloning configuration
        self._reference_audio_path = self._resolve_reference_audio(reference_audio_path)
        self._reference_transcript = reference_transcript or self._load_transcript()
        self._reference_audio_data = None  # lazy-loaded

        cloning_mode = "ultimate" if self._reference_transcript else "controllable"
        logger.info(
            "VoxCPM2 TTS initialized",
            model=model_name,
            device=device,
            cloning_mode=cloning_mode,
            reference_audio=str(self._reference_audio_path) if self._reference_audio_path else None,
        )

    def _resolve_reference_audio(self, path: str | None) -> Path | None:
        """Resolve the reference audio path, checking multiple fallback locations."""
        if path:
            p = Path(path)
            if p.exists():
                return p
            logger.warning("specified reference audio not found", path=path)

        # Fallback: processed reference audio
        if DEFAULT_REFERENCE_AUDIO.exists():
            logger.info("using processed reference audio", path=str(DEFAULT_REFERENCE_AUDIO))
            return DEFAULT_REFERENCE_AUDIO

        # Fallback: raw reference audio
        raw_audio = ASSETS_DIR / "cloning voxcpm2.wav"
        if raw_audio.exists():
            logger.warning(
                "using raw reference audio (run scripts/prepare_voice.py for better quality)",
                path=str(raw_audio),
            )
            return raw_audio

        logger.warning("no reference audio found, voice cloning disabled")
        return None

    def _load_transcript(self) -> str:
        """Load transcript from metadata JSON if available."""
        if DEFAULT_REFERENCE_META.exists():
            try:
                meta = json.loads(DEFAULT_REFERENCE_META.read_text(encoding="utf-8"))
                transcript = meta.get("transcript", "")
                if transcript:
                    logger.info("loaded transcript from metadata", chars=len(transcript))
                return transcript
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("failed to load transcript metadata", error=str(e))
        return ""

    @property
    def model(self) -> str:
        return f"voxcpml2/{self._model_name}"

    @property
    def provider(self) -> str:
        return "voxcpml2"

    @property
    def has_voice_cloning(self) -> bool:
        """Whether voice cloning is active (reference audio available)."""
        return self._reference_audio_path is not None

    @property
    def cloning_mode(self) -> str:
        """Current cloning mode: 'ultimate', 'controllable', or 'none'."""
        if not self.has_voice_cloning:
            return "none"
        return "ultimate" if self._reference_transcript else "controllable"

    async def _ensure_model(self):
        """Lazy-load the VoxCPM2 model and reference audio."""
        if self._model is None:
            loop = asyncio.get_running_loop()

            def _load():
                logger.info("loading VoxCPM2 model", model=self._model_name, device=self._device)

                try:
                    # Try loading via voxcpm package (preferred)
                    from voxcpm import VoxCPM

                    model = VoxCPM.from_pretrained(self._model_name)
                    logger.info("VoxCPM2 model loaded via voxcpm package")
                    return {"type": "voxcpm", "model": model}
                except ImportError:
                    logger.info("voxcpm package not available, falling back to transformers pipeline")

                # Fallback: transformers pipeline
                from transformers import pipeline

                p = pipeline(
                    "text-to-speech",
                    model=self._model_name,
                    device=self._device,
                )
                logger.info("VoxCPM2 model loaded via transformers pipeline")
                return {"type": "pipeline", "model": p}

            self._model = await loop.run_in_executor(self._executor, _load)

            # Load reference audio data if available
            if self._reference_audio_path and self._reference_audio_data is None:
                self._reference_audio_data = await loop.run_in_executor(
                    self._executor, self._load_reference_audio
                )

    def _load_reference_audio(self) -> np.ndarray | None:
        """Load reference audio file for voice cloning."""
        if not self._reference_audio_path or not self._reference_audio_path.exists():
            return None

        try:
            import soundfile as sf

            data, sr = sf.read(str(self._reference_audio_path), dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            logger.info(
                "reference audio loaded",
                path=str(self._reference_audio_path),
                duration_s=f"{len(data) / sr:.2f}",
                sr=sr,
            )
            return data
        except ImportError:
            try:
                from scipy.io import wavfile

                sr, data = wavfile.read(str(self._reference_audio_path))
                if data.dtype == np.int16:
                    data = data.astype(np.float32) / 32768.0
                elif data.dtype == np.int32:
                    data = data.astype(np.float32) / 2147483648.0
                if data.ndim > 1:
                    data = np.mean(data, axis=1)
                logger.info("reference audio loaded (scipy)", duration_s=f"{len(data) / sr:.2f}")
                return data
            except ImportError:
                logger.error("neither soundfile nor scipy available for loading reference audio")
                return None
        except Exception as e:
            logger.error("failed to load reference audio", error=str(e))
            return None

    def synthesize(
        self, text: str, *, conn_options: tts.APIConnectOptions = tts.DEFAULT_API_CONNECT_OPTIONS
    ) -> tts.ChunkedStream:
        return VoxCPML2ChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )

    async def aclose(self) -> None:
        """Cleanup resources."""
        self._executor.shutdown(wait=False)
        self._model = None
        self._reference_audio_data = None


def _pcm_bytes_to_audio_frame(
    pcm_data: bytes,
    sample_rate: int,
    num_channels: int,
) -> rtc.AudioFrame:
    """Convert raw PCM 16-bit LE bytes to an rtc.AudioFrame.

    This is the critical bridge between local TTS output and the
    LiveKit Agents pipeline. The AgentSession expects rtc.AudioFrame
    objects, NOT raw bytes.
    """
    samples_per_channel = len(pcm_data) // (BYTES_PER_SAMPLE * num_channels)
    return rtc.AudioFrame(
        data=pcm_data,
        sample_rate=sample_rate,
        num_channels=num_channels,
        samples_per_channel=samples_per_channel,
    )


class VoxCPML2ChunkedStream(tts.ChunkedStream):
    """ChunkedStream implementation for VoxCPM2 with voice cloning support.

    Compatible with LiveKit Agents SDK 1.5.x AudioEmitter lifecycle:
      1. output_emitter.initialize(...)  — set audio format metadata
      2. output_emitter.push(frame)      — push rtc.AudioFrame objects
      3. output_emitter.flush()          — signal end of audio stream
    """

    def __init__(
        self,
        tts: VoxCPML2TTS,
        input_text: str,
        conn_options: tts.APIConnectOptions,
    ) -> None:
        super().__init__(
            tts=tts,
            input_text=input_text,
            conn_options=conn_options,
        )
        self._vox_tts = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        """Run TTS synthesis and emit audio frames to the LiveKit pipeline.

        This method follows the AudioEmitter lifecycle:
          initialize → push (rtc.AudioFrame) → flush
        """
        await self._vox_tts._ensure_model()

        def _synth() -> bytes:
            """Run synthesis in thread pool (blocking GPU/CPU work)."""
            model_info = self._vox_tts._model
            model_type = model_info["type"]
            model = model_info["model"]

            if model_type == "voxcpm":
                return self._synth_voxcpm(model)
            else:
                return self._synth_pipeline(model)

        loop = asyncio.get_running_loop()
        pcm_bytes = await loop.run_in_executor(self._vox_tts._executor, _synth)

        request_id = shortuuid.uuid()
        logger.info(
            "tts synthesis complete",
            chars=len(self.input_text),
            pcm_bytes=len(pcm_bytes),
            cloning_mode=self._vox_tts.cloning_mode,
            request_id=request_id,
        )

        # ── AudioEmitter lifecycle ──────────────────────────────────────
        # Step 1: Initialize the emitter with audio format metadata
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._vox_tts._sample_rate,
            num_channels=self._vox_tts._num_channels,
            mime_type="audio/pcm",
        )

        # Step 2: Convert PCM bytes → rtc.AudioFrame and push
        # Split into smaller chunks (~200ms each) for responsive playback
        # and proper interruption handling by LiveKit
        chunk_duration_ms = 200
        samples_per_chunk = int(self._vox_tts._sample_rate * chunk_duration_ms / 1000)
        bytes_per_chunk = samples_per_chunk * BYTES_PER_SAMPLE * self._vox_tts._num_channels

        for offset in range(0, len(pcm_bytes), bytes_per_chunk):
            chunk = pcm_bytes[offset : offset + bytes_per_chunk]
            if not chunk:
                break

            frame = _pcm_bytes_to_audio_frame(
                pcm_data=chunk,
                sample_rate=self._vox_tts._sample_rate,
                num_channels=self._vox_tts._num_channels,
            )
            output_emitter.push(frame)

        # Step 3: Flush to signal end of audio stream
        output_emitter.flush()

    def _synth_voxcpm(self, model) -> bytes:
        """Synthesize using the native voxcpm package with voice cloning."""
        ref_audio_path = self._vox_tts._reference_audio_path

        if ref_audio_path and ref_audio_path.exists():
            # Voice cloning mode
            generate_kwargs = {
                "text": self.input_text,
                "prompt_audio": str(ref_audio_path),
            }
            # Ultimate cloning: include transcript for highest fidelity
            if self._vox_tts._reference_transcript:
                generate_kwargs["prompt_text"] = self._vox_tts._reference_transcript

            logger.debug(
                "synthesizing with voice cloning",
                mode=self._vox_tts.cloning_mode,
                text_len=len(self.input_text),
            )
            wav = model.generate(**generate_kwargs)
        else:
            # Standard TTS (no cloning)
            wav = model.generate(text=self.input_text)

        return self._wav_to_pcm_bytes(wav)

    def _synth_pipeline(self, pipeline) -> bytes:
        """Synthesize using HuggingFace transformers pipeline (fallback).

        Note: Pipeline fallback does not support voice cloning directly.
        It uses voice_preset if available.
        """
        forward_params = {}
        if self._vox_tts._voice_preset:
            forward_params["speaker_embeddings"] = self._vox_tts._voice_preset

        output = pipeline(
            self.input_text,
            forward_params=forward_params if forward_params else {},
        )

        audio_array = output["audio"] if isinstance(output, dict) else output
        return self._wav_to_pcm_bytes(audio_array)

    @staticmethod
    def _wav_to_pcm_bytes(wav) -> bytes:
        """Convert model output (numpy/torch) to 16-bit PCM LE bytes."""
        if isinstance(wav, np.ndarray):
            audio = wav
        elif hasattr(wav, "cpu"):
            # torch tensor
            audio = wav.cpu().numpy()
        else:
            audio = np.array(wav)

        # Flatten to 1D if needed
        if audio.ndim > 1:
            audio = audio.squeeze()

        # Ensure float32 range [-1.0, 1.0] → int16
        audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        return audio_int16.tobytes()


# Factory function
def create_voxcpml2_tts(
    model_name: str = "openbmb/VoxCPM2",
    device: str = DEFAULT_DEVICE,
    voice_preset: str | None = None,
    reference_audio_path: str | None = None,
    reference_transcript: str | None = None,
) -> VoxCPML2TTS:
    """Create VoxCPML2 TTS instance with optional voice cloning.

    Args:
        model_name: HuggingFace model ID or local path.
        device: Device to run on ('cuda', 'cpu', 'auto').
        voice_preset: Voice preset for pipeline fallback mode.
        reference_audio_path: Path to reference audio for voice cloning.
        reference_transcript: Transcript of reference audio (for Ultimate Cloning).
    """
    return VoxCPML2TTS(
        model_name=model_name,
        device=device,
        voice_preset=voice_preset,
        reference_audio_path=reference_audio_path,
        reference_transcript=reference_transcript,
    )