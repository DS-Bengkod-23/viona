"""Endpoint /tts (jalur native): guard konfigurasi & validasi input.

Sengaja TIDAK memanggil Cartesia — yang diuji cuma cabang yang berjalan sebelum
request keluar, supaya tes tetap deterministik dan tanpa jaringan/biaya.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.core.config import settings


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_503_when_api_key_missing(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Tanpa CARTESIA_API_KEY -> 503, sinyal bagi frontend untuk fallback Web Speech."""
    monkeypatch.setattr(settings, "cartesia_api_key", "", raising=False)
    resp = client.post("/tts", json={"text": "halo"})
    assert resp.status_code == 503


def test_400_when_text_empty_after_normalization(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """Teks yang habis setelah normalisasi tak boleh diteruskan ke Cartesia."""
    monkeypatch.setattr(settings, "cartesia_api_key", "dummy-key", raising=False)
    resp = client.post("/tts", json={"text": "   "})
    assert resp.status_code == 400


def test_422_when_text_field_missing(client: TestClient):
    assert client.post("/tts", json={}).status_code == 422
