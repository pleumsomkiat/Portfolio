from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from ..settings import Settings


async def deliver_to_robot(
    *, text: str, mp3_path: str | None, settings: Settings
) -> str:
    """Run the SDK2 bridge only after the explicit configuration safety gate."""
    if not settings.robot_audio_enabled:
        return "ปิดการส่งเสียงไปหุ่นยนต์ (ค่าปลอดภัยเริ่มต้น)"
    if not settings.robot_interface or not settings.robot_bridge_bin:
        return "ไม่ส่งไปหุ่นยนต์: ต้องตั้ง ROBOT_INTERFACE และ ROBOT_BRIDGE_BIN"

    bridge = Path(settings.robot_bridge_bin)
    if not bridge.is_file():
        return f"ไม่ส่งไปหุ่นยนต์: ไม่พบ bridge ที่ {bridge}"

    if settings.tts_provider.lower() == "unitree":
        command = [
            str(bridge),
            "--interface",
            settings.robot_interface,
            "--native-text",
            text,
            "--speaker-id",
            str(settings.robot_speaker_id),
        ]
    elif mp3_path:
        wav_path = Path(mp3_path).with_suffix(".wav")
        try:
            await _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    mp3_path,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(wav_path),
                ],
                timeout=45,
            )
        except RuntimeError as exc:
            return f"แปลงเสียงสำหรับ G1 ไม่สำเร็จ: {exc}"
        command = [str(bridge), "--interface", settings.robot_interface, "--wav", str(wav_path)]
    else:
        return "ไม่มีเสียงที่จะส่งไปหุ่นยนต์"

    try:
        await _run(command, timeout=90)
        return "ส่ง audio stream ไป G1 แล้ว"
    except RuntimeError as exc:
        return f"ส่งเสียงไป G1 ไม่สำเร็จ: {exc}"


async def _run(command: list[str], timeout: int) -> None:
    def invoke() -> None:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-500:]
            raise RuntimeError(detail or f"exit code {completed.returncode}")

    try:
        await asyncio.to_thread(invoke)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(str(exc)) from exc
