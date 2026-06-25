"""Tests for the Pipecat migration: TTS LaTeX cleaning, RAG tool, handoff."""
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


class _FakeStore:
    def __init__(self) -> None:
        self.updates: dict = {}

    async def update(self, session_id: str, updates: dict) -> dict:
        self.updates.update(updates)
        return self.updates


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


@pytest.mark.asyncio
async def test_escalate_transitions_to_escalation_node(monkeypatch):
    store = _FakeStore()

    async def _fake_get_store():
        return store

    monkeypatch.setattr(flows, "get_session_store", _fake_get_store)

    session = VionaSession(room_name="room-1")
    fm = _FakeFlowManager(session)

    result, next_node = await flows.escalate_to_human({"reason": "marah"}, fm)

    assert session.escalated is True
    assert store.updates.get("escalated") is True
    assert next_node is not None
    assert next_node["name"] == "escalation"
    # The escalation node announces the handoff and exposes transfer tools.
    assert any(a["type"] == "tts_say" for a in next_node["pre_actions"])
    fn_names = {f.name for f in next_node["functions"]}
    assert fn_names == {"connect_human_agent", "take_callback_number"}
    assert isinstance(result, dict)


def test_support_node_has_expected_tools():
    node = flows.create_support_node()
    assert node["name"] == "support"
    names = {f.name for f in node["functions"]}
    assert names == {
        "search_faq",
        "get_customer_info",
        "save_customer_name",
        "file_complaint",
        "escalate_to_human",
    }


def test_session_state_defaults():
    s = VionaSession(room_name="r")
    assert s.room_name == "r"
    assert s.session_id  # uuid generated
    assert s.escalated is False
