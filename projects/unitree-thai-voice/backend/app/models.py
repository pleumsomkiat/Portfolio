from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2000)
    speak: bool = True


class ChatResponse(BaseModel):
    answer: str
    audio_url: str | None = None
    audio_status: str
    robot_status: str


class HealthResponse(BaseModel):
    status: str
    ai_provider: str
    tts_provider: str
    robot_audio_enabled: bool
