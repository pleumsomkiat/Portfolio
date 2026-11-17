import pytest

from backend.app.knowledge import build_knowledge_context, search_knowledge


@pytest.mark.parametrize("question, fact", [
    ("Unitree G1 สูงเท่าไหร่", "132"),
    ("G1 หนักเท่าไหร่", "35"),
    ("G1 weight", "35"),
])
def test_robot_specs_outrank_company_mentions(question, fact):
    results = search_knowledge(question)
    assert results[0]["source"] == "unitree_g1.md"
    assert fact in results[0]["content"]
    assert fact in build_knowledge_context(question)


@pytest.mark.parametrize("company", [
    "ออโต ไดแด็กติก", "ออโต้ไดแดคติก", "Auto Didactic", "auto-didactic",
])
def test_company_aliases_find_contact_details(company):
    results = search_knowledge(f"{company} อยู่ที่ไหน เบอร์โทรอะไร")
    assert results[0]["source"] == "auto_didactic.md"
    assert "02-311-2717" in results[0]["content"]
    assert "111" in results[0]["content"]


def test_generic_robot_question_prefers_robot_document():
    result = search_knowledge("G1 คืออะไร")[0]
    assert result["source"] == "unitree_g1.md"
    assert "ฮิวแมนนอยด์" in result["content"]


def test_company_history_remains_retrievable():
    result = search_knowledge("บริษัท Auto Didactic ก่อตั้งเมื่อไหร่")[0]
    assert "2543" in result["content"]


def test_unknown_question_has_no_invented_context():
    assert build_knowledge_context("วันนี้กินอะไรดี") == ""


@pytest.mark.parametrize("question", [
    "บริษัทมีอีเมลอะไร", "บริษัทมีอีเมล์อะไร", "บริษัท มี e-mail อะไร",
    "บริษัท email อะไร", "บริษัท มี e mail อะไร",
])
def test_email_question_retrieves_the_unconfirmed_contact_information(question):
    result = search_knowledge(question)[0]
    assert result["source"] == "auto_didactic.md"
    assert "ยังไม่ได้ยืนยันอีเมล" in result["content"]
