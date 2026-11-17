
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re
from threading import Lock

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
from faster_whisper.vad import VadOptions, get_speech_timestamps
from huggingface_hub.errors import LocalEntryNotFoundError

from ..settings import BACKEND_DIR, Settings, get_settings

_model_lock = Lock()

ENGLISH_CONFIDENCE = 0.90


def format_robot_names(text: str) -> str:
    # Normalize explicit spellings of the model name only. "กี่วัน" is a real
    # duration question and must never be replaced with G1 by a text rule.
    return re.sub(
        r"(?<![a-z0-9])(?:g\s*1|จี\s*(?:วัน|หนึ่ง|1))(?![a-z0-9])",
        "G1", text, flags=re.IGNORECASE,
    )


def select_language(model: WhisperModel, audio, settings: Settings) -> str | None:
    if settings.stt_language == "auto":
        return None
    if settings.stt_language != "thai_first":
        return settings.stt_language

    detected, probability, _ = model.detect_language(audio=audio)
    # Short Thai phrases can be mistaken for Indonesian/Vietnamese or romanized
    # English. Keep Thai unless the audio is confidently detected as English.
    if detected == "en" and probability >= ENGLISH_CONFIDENCE:
        return "en"
    return "th"


@lru_cache(maxsize=1)
def get_model():
    settings = get_settings()
    options = {
        "device": settings.stt_device,
        "compute_type": settings.stt_compute_type,
        "cpu_threads": settings.stt_cpu_threads,
    }
    model_name = settings.stt_model
    # Resolve local model folders from the project, regardless of server cwd.
    model_path = BACKEND_DIR.parent / Path(model_name)
    if model_path.is_dir():
        model_name = str(model_path)
    try:
        # A cached model must work even when the external speech service is offline.
        return WhisperModel(model_name, local_files_only=True, **options)
    except LocalEntryNotFoundError:
        return WhisperModel(model_name, **options)


def warm_up_model(model: WhisperModel) -> None:
    if model.model.device != "cuda":
        return
    # Initialize CUDA/cuDNN kernels at startup instead of on the first question.
    # This synthetic silence is not a user recording; its result is discarded.
    segments, _ = model.transcribe(
        np.zeros(16000, dtype=np.float32),
        language="th", task="transcribe", beam_size=5, max_new_tokens=1,
        temperature=0.0, without_timestamps=True, condition_on_previous_text=False,
        vad_filter=False,
    )
    for _ in segments:
        pass


def transcribe_audio(
    audio_bytes: bytes,
    suffix: str = ".webm",
) -> str:
    # Decode directly from memory; do not save microphone input to disk.
    with _model_lock:
        settings = get_settings()
        with BytesIO(audio_bytes) as source:
            audio = decode_audio(source, sampling_rate=16000)
        # Gate non-speech only. Keep the original waveform, including quiet word
        # endings, rather than cutting the audio into VAD-selected fragments.
        if not len(audio) or not get_speech_timestamps(
            audio, VadOptions(threshold=0.35, min_speech_duration_ms=150)
        ):
            return ""
        model = get_model()
        language = select_language(model, audio, settings)
        # Conversation is unrestricted. Company names must not bias every
        # utterance; a spelling hint is applied only when explicitly configured.
        prompt = settings.stt_initial_prompt.strip() or None
        segments, _ = model.transcribe(
            audio,
            language=language,
            task="transcribe",
            beam_size=5,
            vad_filter=False,
            initial_prompt=prompt,
            hotwords=settings.stt_hotwords.strip() or None,
            without_timestamps=True,
            condition_on_previous_text=False,
            repetition_penalty=1.1,
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()
        return format_robot_names(text)
