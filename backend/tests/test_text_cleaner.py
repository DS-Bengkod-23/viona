"""Tests for math/LaTeX -> spoken-Indonesian cleaning in normalize_for_tts."""
from __future__ import annotations

import pytest

from app.core.text_cleaner import normalize_for_tts


@pytest.mark.parametrize(
    "raw, must_contain, must_not_contain",
    [
        # Plain-text math (the cases the LLM actually emits)
        ("Jadi 3 x 4 = 12.", ["3 kali 4", "sama dengan 12"], ["x 4"]),
        ("Hitung 2^3 lalu 10 / 2.", ["2 pangkat 3", "10 bagi 2"], ["2^3", "10 / 2"]),
        ("Nilai x^2 + 5.", ["x pangkat 2", "tambah 5"], ["x^2", "+ 5"]),
        ("Luas x².", ["pangkat 2"], ["²"]),
        (
            "Cek 5 ≥ 3 dan 4 ≤ 9.",
            ["lebih dari atau sama dengan", "kurang dari atau sama dengan"],
            ["≥", "≤"],
        ),
        ("Suhu 5 - 2 derajat.", ["5 kurang 2"], []),
        # LaTeX delimited
        (r"Hasil $\frac{1}{2}$ ok.", ["1 per 2"], ["\\frac", "$"]),
        (r"Akar \sqrt{16}.", ["akar 16"], ["\\sqrt"]),
        # Decimal comma -> "koma" (not split into "125, 43")
        ("Hasilnya 125,43 rupiah.", ["125 koma 43"], ["125, 43"]),
        # \approx expands to "kira-kira" — its hyphen must NOT become "kurang"
        (
            r"Nilai $10 / 7 \approx 1,43$ ya.",
            ["kira-kira", "10 bagi 7", "1 koma 43"],
            ["kira kurang"],
        ),
        # '/' is "bagi" consistently, in plain text and inside $...$
        (r"Plain 6 / 3 dan $8 / 4$.", ["6 bagi 3", "8 bagi 4"], [" per "]),
        # 'x' separated from its digit by punctuation / sentence boundary
        ("Jadi 2. x 2 = 4.", ["2 kali 2"], [" x 2"]),
        # Markdown list dash must not become "kurang"
        ("- 2 x 2\n- 3 x 3", ["2 kali 2", "3 kali 3"], ["kurang"]),
        # Variable x in prose must stay intact (not multiplication)
        ("nilai x adalah 5.", ["nilai x adalah"], ["kali"]),
        # Safety: ordinary prose must stay intact
        ("anak-anak main bola.", ["anak-anak"], ["kurang"]),
        ("pilih ya/tidak dulu.", ["ya/tidak"], ["bagi"]),
        ("tanggal 10/06/2026.", ["10 06 2026"], ["bagi"]),
    ],
)
def test_math_to_speech(raw, must_contain, must_not_contain):
    out = normalize_for_tts(raw)
    for s in must_contain:
        assert s in out, f"{s!r} missing from {out!r}"
    for s in must_not_contain:
        assert s not in out, f"{s!r} should not be in {out!r}"


def test_empty():
    assert normalize_for_tts("") == ""
