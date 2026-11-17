"""Guard sourced company facts and product routing against plausible wrong replies."""

from datetime import date

import pytest

from backend.app.services.keyword_reply import (
    CANNOT_ANSWER,
    classify_keyword_reply,
    load_responses,
)


@pytest.mark.parametrize("question", [
    "ผู้บริหารของบริษัทออโตไดแด็กติกคือใคร",
    "ผู้บริหารคือใคร",
    "ใครเป็นผู้บริหารครับ",
    "กรรมการผู้จัดการคือใคร",
    "ผู้ บริหาร ของ บริษัท คือ ใคร ครับ",
    "Auto Didactic managing director คือใคร",
])
def test_management_answer_identifies_role_and_dated_evidence(question):
    decision = classify_keyword_reply(question)
    assert decision.kind == "prepared"
    assert decision.rule_ids == ("company_management",)
    assert "ฉัตรชัย สมิตกาญจน์" in decision.answer
    assert "กรรมการผู้จัดการ" in decision.answer
    assert "4 กันยายน 2569" in decision.answer
    assert "เจ้าของ" not in decision.answer


def test_management_provenance_keeps_publication_date_separate_from_verification():
    rule = next(rule for rule in load_responses()["rules"] if rule["id"] == "company_management")
    assert rule["source"] == "https://eng.cmu.ac.th/?p=57163"
    assert date.fromisoformat(rule["source_published_at"]) == date(2026, 9, 4)
    assert date.fromisoformat(rule["verified_at"]) >= date.fromisoformat(rule["source_published_at"])


@pytest.mark.parametrize("question", [
    "บริษัทออโตไดแด็กติกขายสินค้าอะไรบ้าง",
    "บริษัท ออโต ไดแด็กติก มีผลิตภัณฑ์อะไรบ้างครับ",
    "มีผลิตภัณฑ์อะไรบ้าง",
    "สินค้าของบริษัทมีอะไรบ้าง",
])
def test_product_overview_includes_training_fields_and_named_examples(question):
    decision = classify_keyword_reply(question)
    assert decision.kind == "prepared"
    assert decision.rule_ids == ("company_products",)
    for fact in ["นิวแมติกส์", "ไฮดรอลิกส์", "DOBOT", "Hanback", "Automation Studio"]:
        assert fact in decision.answer


def test_named_brand_catalog_beats_general_company_product_list():
    decision = classify_keyword_reply("บริษัทมีสินค้า DOBOT รุ่นอะไรบ้าง")
    assert decision.kind == "prepared"
    assert decision.rule_ids == ("company_dobot_catalog",)
    assert "MG400" in decision.answer
    assert "CR COBOT" in decision.answer


@pytest.mark.parametrize("question, rule_id, expected_fact", [
    ("บริษัทออโตไดแด็กติกมีสินค้า DOBOT Magician Lite คืออะไร", "company_dobot_magician_lite", "ประถม"),
    ("DOBOT Magician คืออะไร", "company_dobot_magician", "พิมพ์สามมิติ"),
    ("DOBOT MG400 รับน้ำหนักได้เท่าไหร่", "company_dobot_mg400", "750 กรัม"),
    ("AIoT Autocar คืออะไร", "company_aiot_autocar", "Python 3"),
    ("AIoT SerBOT รวม LiDAR หรือไม่", "company_aiot_serbot", "อุปกรณ์เสริม"),
    ("FAS 7 Station มีกี่สถานี", "company_fas_stations", "7 สถานี"),
    ("บริษัทมีชุดฝึกระบบอัตโนมัติอะไรบ้าง", "company_mpu_mps", "MPU-B Plus"),
    ("บริษัทมีซอฟต์แวร์อะไรบ้าง", "company_automation_studio", "Automation Studio"),
])
def test_specific_product_question_returns_matching_model_facts(question, rule_id, expected_fact):
    decision = classify_keyword_reply(question)
    assert decision.kind == "prepared"
    assert decision.rule_ids == (rule_id,)
    assert expected_fact in decision.answer


def test_magician_lite_does_not_inherit_magician_tool_capabilities():
    answer = classify_keyword_reply("DOBOT Magician Lite ใช้งานอย่างไร").answer
    assert "ประถม" in answer
    assert "พิมพ์สามมิติ" not in answer
    assert "แกะสลักเลเซอร์" not in answer


@pytest.mark.parametrize("question", [
    "บริษัท Google ผู้บริหารคือใคร",
    "บริษัท Google ขาย DOBOT ไหม",
    "บริษัท Google ขายสินค้า Hanback อะไรบ้าง",
    "บริษัทมีผู้ถือหุ้นชื่ออะไร",
    "ใครเป็นเจ้าของบริษัทออโตไดแด็กติก",
    "ใครเป็นเจ้าของบริษัท",
    "บริษัทมีอีเมลอะไร",
    "DOBOT MG400 ราคาปัจจุบันเท่าไหร่",
    "บริษัทมีสต็อก DOBOT Magician ไหม",
    "Hanback รับประกันกี่ปี",
])
def test_unsupported_company_claims_do_not_receive_related_but_wrong_facts(question):
    decision = classify_keyword_reply(question)
    assert decision.kind == "protected"
    assert decision.answer == CANNOT_ANSWER


@pytest.mark.parametrize("product", [
    "DOBOT", "Hanback", "Automation Studio", "FAS", "MPU", "MPS",
    "Mechatronic Kit", "AIoT Autocar", "SerBOT", "Magician Lite", "MG400", "PyC Basic",
    "CR COBOT", "SA3-400", "SA6-600", "IoT Smart Server Plus", "AI Nvidia RoboEX nano",
])
def test_standalone_product_names_protect_unknown_specs_from_general_ai(product):
    decision = classify_keyword_reply(f"{product} กินไฟกี่วัตต์")
    assert decision.kind == "protected"
    assert decision.answer == CANNOT_ANSWER


@pytest.mark.parametrize("question", ["AI คืออะไร", "IoT คืออะไร", "พลังงานทดแทนคืออะไร"])
def test_product_catalog_does_not_protect_generic_science_terms(question):
    assert classify_keyword_reply(question).kind == "unmatched"
