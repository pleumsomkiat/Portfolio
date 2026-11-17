import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.services import keyword_reply
from backend.app.services.ai import GENERAL_SYSTEM_PROMPT, SYSTEM_PROMPT, generate_reply
from backend.app.settings import Settings


def hybrid_settings(**overrides):
    return Settings(_env_file=None, ai_provider="hybrid", ollama_model="qwen2.5:3b", **overrides)


@pytest.fixture
def ollama(monkeypatch):
    calls = []

    class LocalClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, *, json):
            calls.append((url, json))
            return httpx.Response(200, json={"message": {
                "thinking": "Internal reasoning is separate from the visible answer.",
                "content": "คำตอบจาก AI ทั่วไปครับ",
            }},
                                  request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", LocalClient)
    return calls


@pytest.mark.parametrize("question", [
    "หนึ่งบวกหนึ่งได้เท่าไหร่", "วันนี้กินอะไรดี", "ช่วยอธิบายการเขียนโปรแกรม Python",
    "ทำไมตึกถึงสูง",  # A catalog keyword alone does not make this a G1 fact.
])
def test_general_questions_use_local_model_without_company_context(ollama, question):
    answer = asyncio.run(generate_reply(question, hybrid_settings(), "INCIDENTAL COMPANY DOCUMENT"))
    assert answer == "คำตอบจาก AI ทั่วไปครับ"
    assert len(ollama) == 1
    url, payload = ollama[0]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert payload["model"] == "qwen2.5:3b"
    assert payload["messages"][1] == {"role": "user", "content": question}
    assert "INCIDENTAL COMPANY DOCUMENT" not in payload["messages"][0]["content"]
    assert "ไม่มีเครื่องมือค้นเว็บสด" in payload["messages"][0]["content"]
    assert payload["messages"][0]["content"] == GENERAL_SYSTEM_PROMPT
    for term in ("Unitree", "G1", "หุ่นยนต์", "ออโต", "Didactic", "ลำโพง"):
        assert term not in payload["messages"][0]["content"]


def test_legacy_model_mode_retains_its_knowledge_prompt(ollama):
    settings = Settings(_env_file=None, ai_provider="ollama")
    asyncio.run(generate_reply("คำถามทดสอบ", settings, "VERIFIED KNOWLEDGE"))
    prompt = ollama[0][1]["messages"][0]["content"]
    assert prompt.startswith(SYSTEM_PROMPT)
    assert "VERIFIED KNOWLEDGE" in prompt


@pytest.mark.parametrize("think", [None, False, True])
def test_ollama_thinking_option_is_only_sent_when_configured(ollama, think):
    settings = hybrid_settings(ollama_think=think)
    answer = asyncio.run(generate_reply("หนึ่งบวกหนึ่งได้เท่าไหร่", settings))
    payload = ollama[0][1]
    if think is None:
        assert "think" not in payload
    else:
        assert payload["think"] is think
    assert answer == "คำตอบจาก AI ทั่วไปครับ"
    assert "Internal reasoning" not in answer


@pytest.mark.parametrize("question, expected", [
    ("G1 สูงเท่าไหร่", "132"),
    ("บริษัทอยู่ที่ไหน", "สุขุมวิท 62/1"),
    ("สวัสดีครับ", "สวัสดีครับ"),
])
def test_prepared_questions_bypass_general_model(ollama, question, expected):
    assert expected in asyncio.run(generate_reply(question, hybrid_settings()))
    assert ollama == []


@pytest.mark.parametrize("question", [
    "บริษัท ออโต ไดแด็กติก มีรายได้เท่าไหร่", "G1 ราคาเท่าไหร่",
    "Unitree Go2 หนักเท่าไหร่", "G12 สูงเท่าไหร่", "H1 ทำอะไรได้บ้าง",
    "G1 สูงเท่าไหร่ และหนักเท่าไหร่", "บริษัท Google ก่อตั้งเมื่อไหร่",
])
def test_unknown_or_ambiguous_protected_questions_never_reach_model(ollama, question):
    answer = asyncio.run(generate_reply(question, hybrid_settings()))
    assert answer in {keyword_reply.CANNOT_ANSWER, keyword_reply.NOT_UNDERSTOOD}
    assert ollama == []


def test_routing_uses_decision_kind_instead_of_answer_text(ollama, monkeypatch, tmp_path):
    catalog = tmp_path / "responses.json"
    catalog.write_text(json.dumps({
        "topics": [], "unavailable_keywords": [], "rules": [{
            "id": "custom", "questions": ["คำถามทดสอบ"],
            "answer": keyword_reply.NOT_UNDERSTOOD,
        }],
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(keyword_reply, "RESPONSES_PATH", catalog)
    assert asyncio.run(generate_reply("คำถามทดสอบ", hybrid_settings())) == keyword_reply.NOT_UNDERSTOOD
    assert ollama == []


def test_keyword_only_mode_still_does_not_call_model(ollama):
    settings = Settings(_env_file=None, ai_provider="keywords")
    assert asyncio.run(generate_reply("หนึ่งบวกหนึ่งได้เท่าไหร่", settings)) == keyword_reply.NOT_UNDERSTOOD
    assert ollama == []


def test_hybrid_capabilities_describe_both_answer_modes(ollama):
    answer = asyncio.run(generate_reply("คุณช่วยอะไรได้บ้าง", hybrid_settings()))
    assert "คำถามทั่วไปให้ AI ช่วยตอบ" in answer
    assert "ใช้คำตอบที่ยืนยันไว้" in answer
    assert ollama == []


@pytest.mark.parametrize("question", [
    "บริษัทอื่นขาย DOBOT ไหม", "บริษัทอื่นมีสินค้า Hanback อะไรบ้าง",
    "บริษัท ABC ขาย DOBOT ไหม", "บริษัท XYZ มีสินค้า DOBOT รุ่นอะไรบ้าง",
    "สินค้า Hanback ของบริษัท ABC มีอะไรบ้าง",
])
def test_brand_catalog_does_not_identify_another_company_as_auto_didactic(ollama, question):
    answer = asyncio.run(generate_reply(question, hybrid_settings()))
    assert answer == keyword_reply.CANNOT_ANSWER
    assert ollama == []


@pytest.mark.parametrize("question", [
    "บริษัทมีสินค้า DOBOT รุ่นอะไรบ้าง", "บริษัทมีสินค้า Hanback อะไรบ้าง",
    "บริษัทนี้จำหน่ายผลิตภัณฑ์ DOBOT รุ่นไหนบ้าง", "DOBOT มีอะไรบ้าง",
    "บริษัทออโตไดแด็กติกมีสินค้า DOBOT รุ่นอะไรบ้าง",
])
def test_own_or_clear_unnamed_company_brand_questions_still_use_catalog(ollama, question):
    decision = keyword_reply.classify_keyword_reply(question)
    assert decision.kind == "prepared"
    assert decision.rule_ids[0] in {"company_dobot_catalog", "company_hanback_catalog"}
    assert asyncio.run(generate_reply(question, hybrid_settings())) == decision.answer
    assert ollama == []


def test_ollama_failure_is_reported_not_replaced_with_a_fake_answer(monkeypatch):
    class BrokenClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            raise httpx.ConnectError("offline", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", BrokenClient)
    with pytest.raises(RuntimeError, match="เชื่อมต่อ Ollama ไม่สำเร็จ"):
        asyncio.run(generate_reply("หนึ่งบวกหนึ่งได้เท่าไหร่", hybrid_settings()))


def test_api_hybrid_routes_without_broad_search(ollama, monkeypatch):
    monkeypatch.setattr(main, "settings", hybrid_settings(tts_provider="off", robot_audio_enabled=False))
    monkeypatch.setattr(main, "get_model", lambda: None)

    def forbidden(*args, **kwargs):
        pytest.fail("Hybrid routing must not use broad document search")

    monkeypatch.setattr(main, "build_knowledge_context", forbidden)
    with TestClient(main.app) as client:
        general = client.post("/api/chat", json={"message": "หนึ่งบวกหนึ่งได้เท่าไหร่", "speak": False})
        assert general.status_code == 200
        assert general.json()["answer"] == "คำตอบจาก AI ทั่วไปครับ"
        fixed = client.post("/api/chat", json={"message": "G1 สูงเท่าไหร่", "speak": False})
        assert fixed.status_code == 200
        assert "132" in fixed.json()["answer"]
        unknown = client.post("/api/chat", json={"message": "G1 ราคาเท่าไหร่", "speak": False})
        assert unknown.status_code == 200
        assert unknown.json()["answer"] == keyword_reply.CANNOT_ANSWER
        assert client.get("/health").json()["ai_provider"] == "hybrid"
    assert len(ollama) == 1
