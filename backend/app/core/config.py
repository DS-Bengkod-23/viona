from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LiveKit
    livekit_url: str = Field(...)
    livekit_api_key: str = Field(...)
    livekit_api_secret: str = Field(...)

    # Cartesia TTS
    cartesia_api_key: str = Field(...)
    cartesia_voice_id: str = Field(default="a167e0f3-df7e-4d52-a9c3-f949145efdab")
    cartesia_model: str = Field(default="sonic-multilingual")

    # VoxCPM2 TTS (local)
    voxcpm2_enabled: bool = Field(default=False)
    voxcpm2_model_name: str = Field(default="suno/bark")
    voxcpm2_device: str = Field(default="cuda")
    voxcpm2_voice_preset: str | None = Field(default=None)

    # Ollama LLM
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="llama3.2:3b")
    ollama_api_key: str = Field(default="ollama")

    # Embedding (di-offload ke Ollama; all-minilm = 384-dim, cocok collection Qdrant)
    embedding_model: str = Field(default="all-minilm")
    # Dimensi vektor embedding. Biarkan None agar terdeteksi otomatis dari Ollama saat
    # startup (portabel lintas model). Set angka (mis. 768) untuk override eksplisit.
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

    # Twilio
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_phone_number: str = Field(default="")
    twilio_sip_trunk_sid: str = Field(default="")

    # Faster-Whisper STT
    whisper_model_size: str = Field(default="large-v3")
    whisper_language: str = Field(default="id")
    whisper_device: str = Field(default="auto")
    whisper_compute_type: str = Field(default="float16")

    # Observability
    log_level: str = Field(default="INFO")
    environment: str = Field(default="production")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
