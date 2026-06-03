"""TTS (Text-to-Speech) infrastructure for Viona.

This module provides TTS implementations for voice synthesis.
Currently supported:
- Cartesia: Cloud TTS with Indonesian voices
- VoxCPM2: Local open-source TTS model

Usage:
    # Cartesia (cloud)
    from app.infrastructure.tts.cartesia import create_cartesia_tts
    tts = create_cartesia_tts(voice_id="...")

    # VoxCPM2 (local)
    from app.infrastructure.tts.voxcpml2 import create_voxcpml2_tts
    tts = create_voxcpml2_tts(model_name="suno/bark")
"""
from __future__ import annotations

# VoxCPM2 TTS
from app.infrastructure.tts.voxcpml2 import VoxCPML2TTS, create_voxcpml2_tts

__all__ = [
    "VoxCPML2TTS",
    "create_voxcpml2_tts",
]