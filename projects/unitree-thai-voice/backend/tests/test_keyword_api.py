import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.settings import Settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings(
        _env_file=None, ai_provider="keywords", tts_provider="off", robot_audio_enabled=False,
    ))
    monkeypatch.setattr(main, "get_model", lambda: None)

    def forbidden(*args, **kwargs):
        pytest.fail("Keyword replies must not call a language model or broad document search")

    monkeypatch.setattr(httpx, "AsyncClient", forbidden)
    monkeypatch.setattr(main, "build_knowledge_context", forbidden)
    with TestClient(main.app) as connection:
        yield connection


@pytest.mark.parametrize("message, answer", [
    ("วันนี้กินอะไรดี", "ไม่เข้าใจคำถามครับ"),
    ("บริษัท ออโต", "ขออภัยครับ ผมยังไม่ทราบคำตอบสำหรับคำถามนี้ครับ"),
    ("บริษัทมีอีเมลอะไร", "ขออภัยครับ ผมยังไม่ทราบคำตอบสำหรับคำถามนี้ครับ"),
])
def test_api_uses_fixed_fallbacks_without_llm_calls(client, message, answer):
    response = client.post("/api/chat", json={"message": message, "speak": False})
    assert response.status_code == 200
    assert response.json()["answer"] == answer


def test_transcript_is_preserved_separately_from_keyword_matching(client, monkeypatch):
    transcript = "ทำ อะไร ได้ บ้าง"
    monkeypatch.setattr(main, "transcribe_audio", lambda *args: transcript)
    response = client.post("/api/transcribe", files={"file": ("question.wav", b"test-input", "audio/wav")})
    assert response.status_code == 200
    assert response.json() == {"text": transcript}
    reply = client.post("/api/chat", json={"message": response.json()["text"], "speak": False})
    assert reply.status_code == 200
    assert "คีย์เวิร์ดที่เตรียมไว้" in reply.json()["answer"]


def test_g1_capability_question_returns_robot_information(client):
    response = client.post("/api/chat", json={"message": "G1 ทำอะไรได้บ้าง", "speak": False})
    assert response.status_code == 200
    assert "ข้อต่อ" in response.json()["answer"]
    assert "ผมรับคำถามผ่านไมโครโฟน" not in response.json()["answer"]


def test_greeting_from_the_video_is_not_rejected_for_the_polite_ending(client):
    response = client.post("/api/chat", json={"message": "สวัสดีครป", "speak": False})
    assert response.status_code == 200
    assert response.json()["answer"].startswith("สวัสดีครับ")
