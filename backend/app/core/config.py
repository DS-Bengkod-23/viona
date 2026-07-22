from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LiveKit
    livekit_url: str = Field(...)
    livekit_api_key: str = Field(...)
    livekit_api_secret: str = Field(...)

    # Cartesia TTS (cloud) — the ACTIVE TTS engine (low-latency, no GPU). Used by
    # BOTH voice paths: the Pipecat pipeline and the native path via POST /tts.
    # VoxCPM2 below is a parked local alternative (see docs/ENV_PROFILES.md).
    cartesia_api_key: str = Field(default="")
    # "Siti - Ad Narrator": satu-satunya suara PEREMPUAN berbahasa Indonesia di
    # katalog Cartesia (dari 832 suara, hanya 2 ber-language "id"). Viona itu
    # persona perempuan, jadi jangan diganti ke voice English tanpa alasan —
    # suaranya jadi terdengar seperti penutur asing.
    cartesia_voice_id: str = Field(default="b441c4fd-4910-4c55-ae56-f0291057e2cc")
    # Matches pipecat.services.cartesia's own default, so both paths sound alike.
    cartesia_model: str = Field(default="sonic-3.5")

    # VoxCPM2 TTS (local, with voice cloning) — PARKED alternative, not wired into
    # _build_tts (which uses Cartesia). Backlogged to GPU (task D).
    # NOTE: defaults are DEV-SAFE (CPU). The prod profile opts into GPU explicitly
    # (voxcpm2_device=cuda). See docs/ENV_PROFILES.md. VoxCPM2 is heavy and needs a
    # GPU to be usable; dev typically sets voxcpm2_enabled=false.
    voxcpm2_enabled: bool = Field(default=True)
    voxcpm2_model_name: str = Field(default="openbmb/VoxCPM2")
    voxcpm2_device: str = Field(default="cpu")
    voxcpm2_voice_preset: str | None = Field(default=None)
    voxcpm2_reference_audio: str | None = Field(default=None)
    voxcpm2_reference_transcript: str | None = Field(default=None)

    # Ollama LLM
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="gemma4:31b-cloud")
    ollama_api_key: str = Field(default="ollama")

    # Embedding (di-offload ke Ollama; qwen3-embedding:0.6b = 1024-dim)
    embedding_model: str = Field(default="qwen3-embedding:0.6b")
    # Dimensi vektor embedding. Biarkan None agar terdeteksi otomatis dari Ollama saat
    # startup (portabel lintas model). Set angka (mis. 1024) untuk override eksplisit.
    embedding_dim: int | None = Field(default=None)

    # Qdrant
    qdrant_url: str = Field(default="http://qdrant:6333")
    qdrant_api_key: str = Field(default="")
    qdrant_collection: str = Field(default="viona_faq")

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0")
    redis_session_ttl: int = Field(default=3600)

    # FastAPI
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_secret_key: str = Field(default="change-me-in-production")

    # Faster-Whisper STT
    # DEV-SAFE defaults: device=auto (picks CPU when no CUDA), compute_type=int8
    # (float16 is INVALID on CPU and raises). Prod profile sets device=cuda +
    # compute_type=float16. See docs/ENV_PROFILES.md.
    whisper_model_size: str = Field(default="large-v3")
    whisper_language: str = Field(default="id")
    whisper_device: str = Field(default="auto")
    whisper_compute_type: str = Field(default="int8")

    # Observability
    log_level: str = Field(default="INFO")
    environment: str = Field(default="production")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
