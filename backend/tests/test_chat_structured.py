"""Ekstraksi JSON structured-output: model cloud sering membungkus JSON dalam
pagar markdown ```json ... ``` atau menambah prosa. _extract_json_obj harus
mengembalikan objek JSON yang bisa di-parse json.loads."""
from __future__ import annotations

import json

from app.api.routes.chat import _extract_json_obj


def test_strips_markdown_json_fence():
    raw = '```json\n{"response": "halo", "bubble": {"type": "insight", "text": "x"}}\n```'
    parsed = json.loads(_extract_json_obj(raw))
    assert parsed["response"] == "halo"
    assert parsed["bubble"]["text"] == "x"


def test_plain_json_passthrough():
    assert json.loads(_extract_json_obj('{"response": "ok"}'))["response"] == "ok"


def test_extracts_object_from_surrounding_prose():
    raw = 'Berikut jawabannya:\n{"response": "ok"}\nSemoga membantu.'
    assert json.loads(_extract_json_obj(raw))["response"] == "ok"
