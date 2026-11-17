import json

import pytest

from backend.app.services import keyword_reply
from backend.app.services.keyword_reply import CANNOT_ANSWER, NOT_UNDERSTOOD, answer_from_keywords


@pytest.mark.parametrize("question, expected_fact", [
    ("ทำอะไรได้บ้าง", "คีย์เวิร์ดที่เตรียมไว้"),
    ("ทำ อะไร ได้ บ้าง ครับ", "คีย์เวิร์ดที่เตรียมไว้"),
    ("คุณช่วยอะไรได้บ้าง", "คีย์เวิร์ดที่เตรียมไว้"),
    ("คุณชื่ออะไรครับ", "ผู้ช่วยเสียงภาษาไทย"),
    ("สวัสดีครับ", "สวัสดีครับ"),
    ("สวัสดีครป", "สวัสดีครับ"),
    ("สวัสดีครัป", "สวัสดีครับ"),
    ("สวัสดีคับ", "สวัสดีครับ"),
    ("สวัสดีค้าบ", "สวัสดีครับ"),
    ("G1 สูงเท่าไหร่", "132"),
    ("จีวัน สูงเท่าไร", "132"),
    ("G 1 height", "132"),
    ("Unitree G1 weight", "35"),
    ("Auto Didactic ก่อตั้งเมื่อไหร่", "2543"),
    ("บริษัทก่อตั้งปีไหนครับ", "2000"),
    ("บริษัทอยู่ที่ไหน", "สุขุมวิท 62/1"),
    ("Auto Didactic phone", "02-311-2717"),
    ("บริษัทขายอะไรบ้าง", "นิวแมติกส์"),
    ("G1 ลำโพงกี่วัตต์", "5 วัตต์"),
    ("คุณเดินได้ไหม", "ไม่ควบคุมการเดิน"),
])
def test_prepared_answers(question, expected_fact):
    assert expected_fact in answer_from_keywords(question)


@pytest.mark.parametrize("question", [
    "วันนี้กินอะไรดี", "หนึ่งบวกหนึ่งได้เท่าไหร่", "อากาศวันนี้เป็นยังไง", "zxqv",
])
def test_unrecognized_questions_are_not_guessed(question):
    assert answer_from_keywords(question) == NOT_UNDERSTOOD


@pytest.mark.parametrize("question", [
    "บริษัท ออโต", "บริษัทมีอีเมลอะไร", "G1 ราคาเท่าไหร่", "G1 แบตเตอรี่ใช้ได้นานเท่าไหร่",
    "บริษัท Google ก่อตั้งเมื่อไหร่", "G12 สูงเท่าไหร่", "G1 มีรายได้เท่าไหร่",
    "หุ่นยนต์ H1 สูงเท่าไหร่", "Unitree H1 สูงเท่าไหร่", "Unitree Go2 หนักเท่าไหร่", "Unitree คืออะไร",
])
def test_missing_facts_and_other_entities_do_not_receive_unrelated_answers(question):
    assert answer_from_keywords(question) == CANNOT_ANSWER


def test_multiple_equal_intents_are_not_arbitrarily_resolved():
    assert answer_from_keywords("G1 สูงเท่าไหร่ และหนักเท่าไหร่") == NOT_UNDERSTOOD


@pytest.mark.parametrize("question", [
    "G1 ทำอะไรได้บ้าง", "g1 ทำ อะไร ได้ บ้าง ครับ", "จีวันทำอะไรได้บ้าง", "G 1 ช่วยอะไรได้บ้าง",
])
def test_robot_capabilities_are_not_the_web_assistant_capabilities(question):
    answer = answer_from_keywords(question)
    assert "ข้อต่อ" in answer
    assert "รุ่น EDU" in answer
    assert "ผมรับคำถามผ่านไมโครโฟน" not in answer


@pytest.mark.parametrize("question", ["กี่วันทำอะไรได้บ้าง", "H1 ทำอะไรได้บ้าง", "กีวันทำอะไรได้บ้าง"])
def test_unknown_or_ambiguous_subject_does_not_fall_back_to_assistant_description(question):
    assert answer_from_keywords(question) in {NOT_UNDERSTOOD, CANNOT_ANSWER}


def test_invalid_keyword_configuration_fails_closed(monkeypatch, tmp_path):
    path = tmp_path / "responses.json"
    path.write_text(json.dumps({"topics": [], "unavailable_keywords": [], "rules": [
        {"id": "bad", "keywords": ["…"], "answer": "should never match"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(keyword_reply, "RESPONSES_PATH", path)
    with pytest.raises(RuntimeError, match="responses_th.json"):
        answer_from_keywords("อะไรก็ได้")


def test_response_file_can_be_updated_without_restarting(monkeypatch, tmp_path):
    path = tmp_path / "responses.json"
    data = {"topics": [], "unavailable_keywords": [], "rules": [
        {"id": "custom", "keywords": ["ทดสอบ"], "answer": "คำตอบแรกครับ"},
    ]}
    monkeypatch.setattr(keyword_reply, "RESPONSES_PATH", path)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert answer_from_keywords("ทดสอบ") == "คำตอบแรกครับ"
    data["rules"][0]["answer"] = "คำตอบใหม่ครับ"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert answer_from_keywords("ทดสอบ") == "คำตอบใหม่ครับ"
