"""Prepare reference audio for VoxCPM2 voice cloning.

This script processes the raw reference audio to ensure optimal quality
for zero-shot voice cloning:
  1. Trim leading/trailing silence
  2. Normalize volume
  3. Resample to 24 kHz mono (VoxCPM2 standard)
  4. Auto-transcribe with Faster-Whisper (for Ultimate Cloning mode)
  5. Save processed audio + metadata JSON

Usage:
    python -m scripts.prepare_voice
    python -m scripts.prepare_voice --input path/to/audio.wav
    python -m scripts.prepare_voice --skip-transcribe
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_INPUT = ASSETS_DIR / "cloning voxcpm2.wav"
DEFAULT_OUTPUT = ASSETS_DIR / "voice_reference_processed.wav"
DEFAULT_META = ASSETS_DIR / "voice_reference.json"
TARGET_SAMPLE_RATE = 24_000
SILENCE_THRESHOLD_DB = -40.0  # dBFS threshold for silence detection
MIN_SILENCE_DURATION_S = 0.1  # minimum silence duration to trim


def _load_audio(path: Path) -> tuple[np.ndarray, int]:
    """Load audio file and return (samples, sample_rate).

    Uses soundfile as primary loader, falls back to scipy.
    """
    try:
        import soundfile as sf

        data, sr = sf.read(str(path), dtype="float32")
        logger.info("loaded audio (soundfile)", path=str(path), sr=sr, shape=data.shape)
        return data, sr
    except ImportError:
        pass

    try:
        from scipy.io import wavfile

        sr, data = wavfile.read(str(path))
        # Convert to float32 [-1, 1]
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0
        elif data.dtype != np.float32:
            data = data.astype(np.float32)
        logger.info("loaded audio (scipy)", path=str(path), sr=sr, shape=data.shape)
        return data, sr
    except ImportError:
        pass

    raise ImportError(
        "Either 'soundfile' or 'scipy' is required. Install with: pip install soundfile"
    )


def _to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert stereo/multi-channel audio to mono."""
    if audio.ndim == 1:
        return audio
    return np.mean(audio, axis=1)


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample audio to target sample rate using linear interpolation."""
    if orig_sr == target_sr:
        return audio
    duration = len(audio) / orig_sr
    target_len = int(duration * target_sr)
    indices = np.linspace(0, len(audio) - 1, target_len)
    resampled = np.interp(indices, np.arange(len(audio)), audio)
    logger.info("resampled", orig_sr=orig_sr, target_sr=target_sr, samples=len(resampled))
    return resampled.astype(np.float32)


def _trim_silence(
    audio: np.ndarray,
    sr: int,
    threshold_db: float = SILENCE_THRESHOLD_DB,
    min_dur: float = MIN_SILENCE_DURATION_S,
) -> np.ndarray:
    """Trim leading and trailing silence from audio."""
    threshold_linear = 10 ** (threshold_db / 20.0)
    frame_len = int(min_dur * sr)
    abs_audio = np.abs(audio)

    # Find start: first frame above threshold
    start = 0
    for i in range(0, len(audio) - frame_len, frame_len):
        if np.max(abs_audio[i : i + frame_len]) > threshold_linear:
            start = max(0, i - frame_len)  # keep small padding
            break

    # Find end: last frame above threshold
    end = len(audio)
    for i in range(len(audio) - frame_len, frame_len, -frame_len):
        if np.max(abs_audio[i : i + frame_len]) > threshold_linear:
            end = min(len(audio), i + 2 * frame_len)  # keep small padding
            break

    trimmed = audio[start:end]
    removed_s = (len(audio) - len(trimmed)) / sr
    logger.info("trimmed silence", removed_seconds=f"{removed_s:.2f}", start=start, end=end)
    return trimmed


def _normalize(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """Normalize audio volume to target peak level in dBFS."""
    peak = np.max(np.abs(audio))
    if peak < 1e-8:
        logger.warning("audio is silent, skipping normalization")
        return audio
    target_linear = 10 ** (target_db / 20.0)
    gain = target_linear / peak
    normalized = audio * gain
    logger.info(
        "normalized",
        original_peak_db=f"{20 * np.log10(peak):.1f}",
        target_db=target_db,
        gain=f"{gain:.3f}",
    )
    return np.clip(normalized, -1.0, 1.0).astype(np.float32)


def _save_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    """Save audio as WAV file."""
    try:
        import soundfile as sf

        sf.write(str(path), audio, sr, subtype="PCM_16")
    except ImportError:
        from scipy.io import wavfile

        audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        wavfile.write(str(path), sr, audio_int16)
    logger.info("saved processed audio", path=str(path), duration_s=f"{len(audio) / sr:.2f}")


def _transcribe(audio_path: Path, language: str = "id") -> str:
    """Auto-transcribe audio using Faster-Whisper for Ultimate Cloning mode."""
    try:
        from faster_whisper import WhisperModel

        logger.info("transcribing reference audio", model="small", language=language)
        model = WhisperModel("small", device="auto", compute_type="int8")
        segments, _info = model.transcribe(str(audio_path), language=language, beam_size=3)
        transcript = " ".join(seg.text.strip() for seg in segments)
        logger.info("transcription complete", transcript=transcript[:100])
        return transcript
    except ImportError:
        logger.warning("faster-whisper not installed, skipping transcription")
        return ""
    except Exception as e:
        logger.error("transcription failed", error=str(e))
        return ""


def prepare_voice(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    meta_path: Path = DEFAULT_META,
    skip_transcribe: bool = False,
) -> dict:
    """Process reference audio and generate metadata.

    Returns:
        dict with keys: output_path, transcript, duration_s, sample_rate
    """
    logger.info("=" * 60)
    logger.info("VoxCPM2 Voice Cloning — Audio Preparation")
    logger.info("=" * 60)

    if not input_path.exists():
        logger.error("input audio not found", path=str(input_path))
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    # Step 1: Load
    audio, sr = _load_audio(input_path)
    logger.info(
        "raw audio",
        duration_s=f"{len(audio) / sr:.2f}",
        sample_rate=sr,
        channels="stereo" if audio.ndim > 1 else "mono",
    )

    # Step 2: Convert to mono
    audio = _to_mono(audio)

    # Step 3: Trim silence
    audio = _trim_silence(audio, sr)

    # Step 4: Normalize volume
    audio = _normalize(audio)

    # Step 5: Resample to target rate
    audio = _resample(audio, sr, TARGET_SAMPLE_RATE)

    # Step 6: Save processed audio
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _save_wav(output_path, audio, TARGET_SAMPLE_RATE)

    duration_s = len(audio) / TARGET_SAMPLE_RATE
    logger.info(
        "processed audio ready",
        duration_s=f"{duration_s:.2f}",
        sample_rate=TARGET_SAMPLE_RATE,
    )

    # Step 7: Auto-transcribe (optional)
    transcript = ""
    if not skip_transcribe:
        transcript = _transcribe(output_path)

    # Step 8: Save metadata
    meta = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "transcript": transcript,
        "duration_s": round(duration_s, 2),
        "sample_rate": TARGET_SAMPLE_RATE,
        "channels": 1,
        "cloning_mode": "ultimate" if transcript else "controllable",
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("metadata saved", path=str(meta_path), mode=meta["cloning_mode"])

    logger.info("=" * 60)
    logger.info("[SUCCESS] Voice preparation complete!")
    if transcript:
        logger.info(f"   Mode: Ultimate Cloning (transcript tersedia)")
        logger.info(f"   Transcript: {transcript[:80]}...")
    else:
        logger.info(f"   Mode: Controllable Cloning (tanpa transcript)")
    logger.info(f"   Output: {output_path}")
    logger.info(f"   Duration: {duration_s:.2f}s")
    logger.info("=" * 60)

    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare reference audio for VoxCPM2 voice cloning")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to raw reference audio (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path for processed output audio (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--meta", "-m",
        type=Path,
        default=DEFAULT_META,
        help=f"Path for metadata JSON (default: {DEFAULT_META})",
    )
    parser.add_argument(
        "--skip-transcribe",
        action="store_true",
        help="Skip auto-transcription step",
    )
    args = parser.parse_args()

    try:
        prepare_voice(
            input_path=args.input,
            output_path=args.output,
            meta_path=args.meta,
            skip_transcribe=args.skip_transcribe,
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("preparation failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
