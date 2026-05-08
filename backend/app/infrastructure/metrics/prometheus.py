from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry(auto_describe=True)

calls_total = Counter(
    "viona_calls_total",
    "Total inbound/outbound calls handled",
    ["direction", "status"],
    registry=REGISTRY,
)

stt_requests_total = Counter(
    "viona_stt_requests_total",
    "Total STT transcription requests",
    ["model", "language"],
    registry=REGISTRY,
)

llm_requests_total = Counter(
    "viona_llm_requests_total",
    "Total LLM inference requests",
    ["model", "status"],
    registry=REGISTRY,
)

tts_requests_total = Counter(
    "viona_tts_requests_total",
    "Total TTS synthesis requests",
    ["model"],
    registry=REGISTRY,
)

rag_queries_total = Counter(
    "viona_rag_queries_total",
    "Total RAG retrieval queries",
    ["collection"],
    registry=REGISTRY,
)

escalations_total = Counter(
    "viona_escalations_total",
    "Total human escalation events",
    ["reason"],
    registry=REGISTRY,
)

stt_latency_seconds = Histogram(
    "viona_stt_latency_seconds",
    "STT end-to-end latency in seconds",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0],
    registry=REGISTRY,
)

llm_latency_seconds = Histogram(
    "viona_llm_latency_seconds",
    "LLM first-token latency in seconds",
    buckets=[0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0],
    registry=REGISTRY,
)

tts_latency_seconds = Histogram(
    "viona_tts_latency_seconds",
    "TTS first-audio-chunk latency in seconds",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0],
    registry=REGISTRY,
)

active_sessions = Gauge(
    "viona_active_sessions",
    "Currently active voice sessions",
    registry=REGISTRY,
)

agent_ready = Gauge(
    "viona_agent_ready",
    "Whether the LiveKit agent worker is accepting jobs (1=yes, 0=no)",
    registry=REGISTRY,
)


def metrics_output() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
