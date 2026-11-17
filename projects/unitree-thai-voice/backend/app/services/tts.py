from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from ..settings import Settings


@dataclass(frozen=True)
class TtsResult:
    mp3_path: str | None
    status: str


async def synthesize_thai(text: str, settings: Settings) -> TtsResult:
    provider = settings.tts_provider.lower().strip()
    if provider == "off":
        return TtsResult(None, "ปิด TTS")
    if provider == "unitree":
        return TtsResult(None, "ใช้ Unitree native TTS (ไม่มีไฟล์เสียงสำหรับ browser)")
    if provider != "edge":
        return TtsResult(None, "TTS_PROVIDER ต้องเป็น edge, unitree หรือ off")

    try:
        import edge_tts

        output = settings.audio_dir / f"{uuid4().hex}.mp3"
        # Keep requests bounded; this endpoint is a chat voice response, not long-form TTS.
        await edge_tts.Communicate(text[:1800], settings.edge_tts_voice).save(str(output))
        return TtsResult(str(output), "สร้างเสียงภาษาไทยด้วย Edge TTS แล้ว")
    except Exception as exc:  # TTS failure must not hide a valid chat answer.
        return TtsResult(None, f"สร้างเสียงไม่สำเร็จ: {exc}")
