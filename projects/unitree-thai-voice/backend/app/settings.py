from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration loaded only from backend/.env and environment."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    ai_provider: str = "keywords"
    hybrid_ai_provider: Literal["ollama", "openai"] = "ollama"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_think: bool | None = None

    tts_provider: str = "edge"
    edge_tts_voice: str = "th-TH-PremwadeeNeural"
    cors_origins: str = "http://localhost:3000"

    stt_model: str = "small"
    stt_language: Literal["thai_first", "auto", "th", "en"] = "thai_first"
    stt_initial_prompt: str = ""
    stt_hotwords: str = ""
    stt_device: Literal["cpu", "cuda"] = "cpu"
    stt_compute_type: str = "int8"
    stt_cpu_threads: int = Field(default=0, ge=0)

    robot_audio_enabled: bool = False
    robot_interface: str = ""
    robot_bridge_bin: str = ""
    robot_speaker_id: int = 0

    @property
    def audio_dir(self) -> Path:
        path = BACKEND_DIR / "storage" / "audio"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
