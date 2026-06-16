"""Tests for VoxCPML2 TTS implementation."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from livekit.agents import tts
from app.infrastructure.tts.voxcpml2 import VoxCPML2TTS, VoxCPML2ChunkedStream


@patch("app.infrastructure.tts.voxcpml2.pipeline")
def test_voxcpml2_tts_inheritance(mock_pipeline):
    # Initialize the TTS class (pipeline won't be loaded until synthesize/ensure_pipeline)
    vox_tts = VoxCPML2TTS(model_name="suno/bark", device="cpu")
    assert isinstance(vox_tts, tts.TTS)
    assert vox_tts.model == "voxcpml2/suno/bark"
    assert vox_tts.provider == "voxcpml2"


@pytest.mark.asyncio
@patch("app.infrastructure.tts.voxcpml2.pipeline")
async def test_voxcpml2_synthesize_returns_chunked_stream(mock_pipeline):
    mock_pipe_inst = MagicMock()
    mock_pipe_inst.return_value = {"audio": [0.1, 0.2, 0.3]}
    mock_pipeline.return_value = mock_pipe_inst

    vox_tts = VoxCPML2TTS(model_name="suno/bark", device="cpu")
    # Calling synthesize should return a ChunkedStream
    stream = vox_tts.synthesize("Halo Viona")
    assert isinstance(stream, tts.ChunkedStream)
