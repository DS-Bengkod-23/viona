"""TTS (Text-to-Speech) infrastructure for Viona.

Provides the local VoxCPM2 TTS (zero-shot voice cloning) as a Pipecat service.

Usage:
    from app.infrastructure.tts.voxcpml2_pipecat import VoxCPML2TTSService
    tts = VoxCPML2TTSService(reference_audio_path="assets/voice_reference_processed.wav")
"""
from __future__ import annotations

from app.infrastructure.tts.voxcpml2_pipecat import VoxCPML2TTSService

__all__ = [
    "VoxCPML2TTSService",
]
