"""Tests for the Pipecat migration: TTS LaTeX cleaning, RAG tool, support node."""
from __future__ import annotations

import pytest

from app.agents import flows, tools
from app.domain.session import VionaSession


class _FakeFlowManager:
    def __init__(self, session: VionaSession) -> None:
        self.state = {"session": session}


class _FakeRetriever:
    async def search(self, query: str, **_kwargs):
        return [{"text": "Refund diproses dalam 14 hari kerja.", "source": "faq.pdf"}]


@pytest.mark.asyncio
async def test_tts_cleans_latex_before_synthesis(monkeypatch):
    """run_tts must pass LaTeX-cleaned, speakable text to the model."""
    from app.infrastructure.tts.voxcpml2_pipecat import VoxCPML2TTSService

    tts = VoxCPML2TTSService(device="cpu")

    captured: dict[str, str] = {}

    def _fake_synth(text: str) -> bytes:
        captured["text"] = text
        return b"\x00\x00" * 1000  # tiny silent PCM

    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(tts, "_ensure_model", _noop)
    monkeypatch.setattr(tts, "_synthesize", _fake_synth)
    monkeypatch.setattr(tts, "start_tts_usage_metrics", _noop)
    monkeypatch.setattr(tts, "stop_ttfb_metrics", _noop)

    frames = [f async for f in tts.run_tts(r"Hasilnya $\frac{1}{2}$ ya.", "ctx") if f]

    assert "text" in captured
    # LaTeX delimiters/commands gone; spoken form present.
    assert "$" not in captured["text"]
    assert "\\frac" not in captured["text"]
    assert "1 per 2" in captured["text"]
    # Audio frames were produced.
    assert frames and all(getattr(f, "audio", None) for f in frames)


@pytest.mark.asyncio
async def test_search_faq_returns_rag_context():
    session = VionaSession(room_name="room-1", retriever=_FakeRetriever())
    fm = _FakeFlowManager(session)

    result, next_node = await tools.search_faq({"query": "refund"}, fm)

    assert next_node is None
    assert "BASIS PENGETAHUAN" in result
    assert "14 hari kerja" in result


@pytest.mark.asyncio
async def test_search_faq_without_retriever():
    session = VionaSession(room_name="room-1", retriever=None)
    result, _ = await tools.search_faq({"query": "x"}, _FakeFlowManager(session))
    assert "tidak tersedia" in result.lower()


def test_support_node_injects_lms_context_and_has_no_tools():
    # LMS pivot: answers come from injected lms_context, not from tools.
    node = flows.create_support_node(lms_context="Materi: dasar HTML dan tag <p>.")
    assert node["name"] == "support"
    assert node["functions"] == []
    assert "KONTEKS MATERI" in node["role_message"]
    assert "dasar HTML" in node["role_message"]


def test_session_state_defaults():
    s = VionaSession(room_name="r")
    assert s.room_name == "r"
    assert s.session_id  # uuid generated
    assert s.escalated is False
