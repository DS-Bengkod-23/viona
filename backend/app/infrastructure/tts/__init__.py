"""TTS (Text-to-Speech) infrastructure for Viona.

This module provides TTS implementations for voice synthesis.
Currently supported:
- VoxCPM2: Local open-source TTS model with zero-shot voice cloning

Usage:
    # VoxCPM2 with voice cloning (recommended)
    from app.infrastructure.tts.voxcpml2 import create_voxcpml2_tts
    tts = create_voxcpml2_tts(
        model_name="openbmb/VoxCPM2",
        reference_audio_path="assets/voice_reference_processed.wav",
    )

    # VoxCPM2 standard (tanpa cloning)
    from app.infrastructure.tts.voxcpml2 import create_voxcpml2_tts
    tts = create_voxcpml2_tts(model_name="openbmb/VoxCPM2")
"""
from __future__ import annotations

# VoxCPM2 TTS
from app.infrastructure.tts.voxcpml2 import VoxCPML2TTS, create_voxcpml2_tts

__all__ = [
    "VoxCPML2TTS",
    "create_voxcpml2_tts",
]