"""Tests for faster-whisper STT helpers."""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np

from app.infrastructure.stt.faster_whisper import FasterWhisperSTT, _frames_to_float32, _TARGET_RATE


def test_frames_to_float32_mono_resamples_48k_to_16k():
    sr = 48_000
    n = 4800
    samples = (np.random.default_rng(0).standard_normal(n) * 8000).astype(np.int16)
    frame = SimpleNamespace(data=samples.tobytes(), num_channels=1, sample_rate=sr)
    out = _frames_to_float32([frame])
    expected = math.ceil(n * _TARGET_RATE / sr)
    assert abs(len(out) - expected) <= 1
    assert out.dtype == np.float32


def test_frames_to_float32_empty():
    assert _frames_to_float32([]).size == 0


def test_faster_whisper_disables_internal_vad_by_default():
    stt = FasterWhisperSTT()
    assert stt._vad_filter is False
