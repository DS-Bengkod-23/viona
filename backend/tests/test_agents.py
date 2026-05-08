"""Basic unit tests for agent utilities."""
from __future__ import annotations

import pytest

from app.infrastructure.rag.ingestion import _chunk_text


def test_chunk_text_empty():
    assert _chunk_text("") == []


def test_chunk_text_short():
    text = "Hello world."
    chunks = _chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == "Hello world."


def test_chunk_text_respects_size():
    word = "a" * 100
    text = " ".join([word] * 20)
    chunks = _chunk_text(text, chunk_size=512, overlap=64)
    for chunk in chunks:
        assert len(chunk) <= 512 + 64


def test_chunk_text_sentence_boundary():
    text = "Sentence one. Sentence two. Sentence three. " * 15
    chunks = _chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1


def test_chunk_text_overlap_produces_duplicate_content():
    text = "word " * 300
    chunks = _chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 2
