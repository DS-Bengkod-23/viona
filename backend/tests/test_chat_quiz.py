"""Guardrail kuis: saat is_quiz, imbuhan system prompt memuat guard (tolak jawaban
soal, TETAP bantu konsep) — bukan lagi memblok semua pertanyaan (deterministik,
tanpa jaringan)."""
from __future__ import annotations

from app.api.routes.chat import _instruction_suffix


def test_quiz_guard_present_when_is_quiz():
    suffix = _instruction_suffix(is_quiz=True)
    assert "HALAMAN KUIS" in suffix
    assert "DILARANG" in suffix        # tolak jawaban langsung
    assert "KONSEP" in suffix          # tapi tetap bantu konsep


def test_no_quiz_guard_when_not_quiz():
    assert "HALAMAN KUIS" not in _instruction_suffix(is_quiz=False)
