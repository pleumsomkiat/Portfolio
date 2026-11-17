from io import BytesIO
from types import SimpleNamespace
import wave

import numpy as np
import pytest

from backend.app.services import stt
from backend.app.settings import Settings


def wav_bytes(audio):
    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
        return buffer.getvalue()


@pytest.mark.parametrize("signal", ["silence", "tone", "noise"])
def test_non_speech_is_not_decoded_into_a_question(monkeypatch, signal):
    audio = np.zeros(32000, dtype=np.float32)
    if signal == "tone":
        audio = 0.1 * np.sin(2 * np.pi * 440 * np.arange(32000) / 16000)
    elif signal == "noise":
        audio = np.random.default_rng(42).normal(0, 0.01, 32000)
    monkeypatch.setattr(stt, "get_model", lambda: pytest.fail("Non-speech reached Whisper"))
    assert stt.transcribe_audio(wav_bytes(audio), ".wav") == ""


@pytest.mark.parametrize("configured_prompt, expected_prompt", [
    ("", None), ("   ", None), ("  คำศัพท์ที่ผู้ดูแลระบุ  ", "คำศัพท์ที่ผู้ดูแลระบุ"),
])
def test_general_conversation_has_no_implicit_company_prompt(monkeypatch, configured_prompt, expected_prompt):
    settings = Settings(_env_file=None, stt_language="th", stt_initial_prompt=configured_prompt)
    monkeypatch.setattr(stt, "get_settings", lambda: settings)
    # VAD confirms speech in the first second; the complete input must still be
    # decoded so quiet words outside that interval are not removed.
    monkeypatch.setattr(stt, "get_speech_timestamps", lambda *args: [{"start": 0, "end": 16000}])

    class Model:
        def transcribe(self, audio, **options):
            assert options["initial_prompt"] == expected_prompt
            assert len(audio) == 32000
            return iter([SimpleNamespace(text=" วันนี้อยากกินข้าวอะไรดี ")]), None

    monkeypatch.setattr(stt, "get_model", lambda: Model())
    result = stt.transcribe_audio(wav_bytes(np.ones(32000) * 0.02), ".wav")
    assert result == "วันนี้อยากกินข้าวอะไรดี"


@pytest.mark.parametrize("text, expected", [
    ("จีวันทำอะไรได้บ้าง", "G1ทำอะไรได้บ้าง"),
    ("จี วัน ทำอะไรได้บ้าง", "G1 ทำอะไรได้บ้าง"),
    ("จีหนึ่งทำอะไรได้บ้าง", "G1ทำอะไรได้บ้าง"),
    ("g 1 ทำอะไรได้บ้าง", "G1 ทำอะไรได้บ้าง"),
    ("อีกกี่วันจะได้ของ", "อีกกี่วันจะได้ของ"),
    ("กี่วันทำอะไรได้บ้าง", "กี่วันทำอะไรได้บ้าง"),
    ("ชีวันทำอะไรได้บ้าง", "ชีวันทำอะไรได้บ้าง"),
    ("G12 สูงเท่าไหร่", "G12 สูงเท่าไหร่"),
])
def test_model_name_formatting_keeps_duration_words_intact(text, expected):
    assert stt.format_robot_names(text) == expected
