import asyncio

import pytest

from backend.app.knowledge import search_knowledge
from backend.app.services.ai import generate_reply
from backend.app.services.keyword_reply import CANNOT_ANSWER, NOT_UNDERSTOOD, classify_keyword_reply
from backend.app.settings import Settings


@pytest.mark.parametrize("question, fact", [
    ("R1 คืออะไร", "ฮิวแมนนอยด์"),
    ("R1 สูงเท่าไหร่", "123"),
    ("R 1 height", "123"),
    ("อาร์วันสูงเท่าไหร่", "123"),
    ("อาร์ หนึ่ง สูงเท่าไหร่ครับ", "123"),
    ("R1 AIR หนักเท่าไหร่", "27"),
    ("R1 EDU weight", "29"),
    ("R1 มีกี่ข้อต่อ", "26 ถึง 40"),
    ("R1 แบตเตอรี่ใช้ได้นานเท่าไหร่", "1 ชั่วโมง"),
    ("R1 AIR ใช้กล้องอะไร", "ตาเดียว"),
    ("R1 มีกี่รุ่น", "สามรุ่น"),
    ("R1 พัฒนาโปรแกรมได้ไหม", "R1 EDU"),
    ("R1 ลำโพงกี่วัตต์", "ไม่ได้ระบุกำลังวัตต์"),
    ("R1 รองรับ wifi ไหม", "Wi-Fi 6"),
    ("R1 ทำอะไรได้บ้าง", "ฮิวแมนนอยด์"),
])
def test_r1_prepared_answers_bypass_llm(monkeypatch, question, fact):
    def forbidden(*args, **kwargs):
        pytest.fail("Prepared R1 questions must not call an LLM")

    monkeypatch.setattr("httpx.AsyncClient", forbidden)
    decision = classify_keyword_reply(question)
    assert decision.kind == "prepared"
    assert all(rule.startswith("r1_") for rule in decision.rule_ids)
    assert fact in decision.answer
    settings = Settings(_env_file=None, ai_provider="hybrid")
    assert asyncio.run(generate_reply(question, settings)) == decision.answer


@pytest.mark.parametrize("question", [
    "R1 ราคาเท่าไหร่", "R1 วิ่งเร็วเท่าไหร่", "R12 สูงเท่าไหร่",
    "R1 หุ่นยนต์เดินให้ดู", "R1 บริษัทไหนขาย", "R1 มีสินค้าบริษัทอะไรบ้าง",
])
def test_unknown_r1_facts_do_not_use_g1_or_company_answers(question):
    decision = classify_keyword_reply(question)
    assert decision.kind == "protected"
    assert decision.answer in {CANNOT_ANSWER, NOT_UNDERSTOOD}


def test_mixed_model_question_does_not_select_one_model():
    assert classify_keyword_reply("G1 กับ R1 สูงเท่าไหร่").answer == NOT_UNDERSTOOD


@pytest.mark.parametrize("question", ["R1 สูงเท่าไหร่", "R 1 หนักเท่าไหร่", "อาร์วันแบตเตอรี่อยู่ได้นานไหม"])
def test_r1_retrieval_uses_r1_document(question):
    results = search_knowledge(question)
    assert results
    assert all(result["source"] == "unitree_r1.md" for result in results)


def test_g1_retrieval_does_not_include_r1():
    results = search_knowledge("G1 สูงเท่าไหร่")
    assert "132" in results[0]["content"]
    assert all(result["source"] != "unitree_r1.md" for result in results)
