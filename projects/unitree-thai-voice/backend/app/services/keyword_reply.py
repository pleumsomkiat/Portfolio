"""Choose a prepared answer without generating or rewriting any user text."""
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Literal
import unicodedata

from ..knowledge import normalize_text

RESPONSES_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "responses_th.json"
NOT_UNDERSTOOD = "ไม่เข้าใจคำถามครับ"
CANNOT_ANSWER = "ขออภัยครับ ผมยังไม่ทราบคำตอบสำหรับคำถามนี้ครับ"


@dataclass(frozen=True)
class KeywordDecision:
    """Keep routing intent separate from the Thai text returned to the user."""

    kind: Literal["prepared", "protected", "unmatched"]
    answer: str
    rule_ids: tuple[str, ...] = ()


def compact(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFC", text)
                   if unicodedata.category(char)[0] in {"L", "M", "N"})


def question_key(text: str) -> str:
    key = compact(normalize_text(text))
    # Polite endings and ASR word spacing do not change the question's intent.
    endings = ("นะครับ", "นะคับ", "ครับ", "ครัป", "ครป", "นะคะ", "ค่ะ", "คะ", "คับ", "ค้าบ", "หน่อย")
    while key:
        ending = next((ending for ending in endings if key.endswith(ending)), None)
        if ending is None:
            break
        key = key[:-len(ending)]
    return key


def contains_term(question: str, term: str) -> bool:
    term = normalize_text(term)
    if term.isascii():
        # G1 must not match G12; English words must not match word fragments.
        pattern = re.escape(term).replace(r"\ ", r"\s+")
        return re.search(r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])", question) is not None
    return compact(term) in compact(question)


def load_responses() -> dict:
    try:
        data = json.loads(RESPONSES_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
            raise ValueError("rules must be a list")
        for field in ("topics", "unavailable_keywords"):
            values = data.get(field)
            if not isinstance(values, list) or any(not isinstance(value, str) or not compact(value) for value in values):
                raise ValueError(f"{field} must contain non-empty strings")
        seen = set()
        for rule in data["rules"]:
            if not isinstance(rule, dict) or not isinstance(rule.get("id"), str) or not rule["id"].strip() or rule["id"] in seen:
                raise ValueError("each rule needs a unique id")
            seen.add(rule["id"])
            if not isinstance(rule.get("answer"), str) or not rule["answer"].strip():
                raise ValueError("each rule needs an answer")
            if not isinstance(rule.get("priority", 0), int):
                raise ValueError("priority must be an integer")
            for field in ("subjects", "keywords", "questions"):
                values = rule.get(field, [])
                if not isinstance(values, list) or any(not isinstance(value, str) or not compact(value) for value in values):
                    raise ValueError(f"{field} must contain non-empty strings")
            if not rule.get("questions") and not rule.get("keywords"):
                raise ValueError("each rule needs questions or keywords")
        return data
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("อ่านรายการคีย์เวิร์ดและคำตอบไม่ได้ กรุณาตรวจ responses_th.json") from exc


def is_generic_company_product_question(message: str, subjects: list[str]) -> bool:
    """Accept complete unnamed-company questions, not a named firm's catalog.

    A brand match alone cannot establish which company sells it. Exact catalog
    questions are checked separately; these templates cover brand substitutions
    such as 'บริษัทมีสินค้า DOBOT รุ่นอะไรบ้าง' without treating arbitrary text
    after 'บริษัท' as this company's name.
    """
    key = question_key(message)
    prefix = (
        r"(?:บริษัท(?:นี้|ของคุณ|ของเรา)?(?:มี|ขาย|จำหน่าย)"
        r"(?:สินค้า|ผลิตภัณฑ์|ชุดฝึก|แขนกล)?(?:ของ|ยี่ห้อ)?"
        r"|(?:สินค้า|ผลิตภัณฑ์|ชุดฝึก)(?:ของ)?บริษัท(?:นี้)?(?:มี|เป็น)?)"
    )
    suffix = r"(?:(?:รุ่น)?(?:อะไรบ้าง|อะไร|ไหนบ้าง|ไหน|บ้าง|ไหม|หรือไม่|หรือเปล่า)|กี่รุ่น)"
    return any(re.fullmatch(prefix + re.escape(question_key(subject)) + suffix, key)
               is not None for subject in subjects)


def classify_keyword_reply(message: str) -> KeywordDecision:
    catalog = load_responses()
    question = normalize_text(message)
    key = question_key(message)
    if not key:
        return KeywordDecision("protected", NOT_UNDERSTOOD)

    known_topic = any(contains_term(question, term) for term in catalog["topics"])
    # Unlisted Unitree-like model numbers must not be invented by the general
    # model merely because G1's word boundary correctly excludes G12, H1, etc.
    robot_model = re.search(r"(?<![a-z0-9])(?:g|h|go|r)\s*\d+(?![a-z0-9])", question) is not None
    protected_topic = known_topic or robot_model
    if known_topic and any(contains_term(question, term) for term in catalog["unavailable_keywords"]):
        return KeywordDecision("protected", CANNOT_ANSWER)

    r1_subjects = ("r1", "r 1", "อาร์วัน", "อาร์ วัน", "อาร์หนึ่ง", "อาร์ หนึ่ง")
    g1_subjects = ("g1", "g 1", "จีวัน", "จี วัน", "จีหนึ่ง")
    mentions_r1 = any(contains_term(question, term) for term in r1_subjects)
    if mentions_r1 and any(contains_term(question, term) for term in g1_subjects):
        return KeywordDecision("protected", NOT_UNDERSTOOD)

    company_reference = contains_term(question, "บริษัท") or contains_term(question, "company")
    named_company = contains_term(question, "autodidactic")

    matches = []
    recognized_keyword = False
    for rule in catalog["rules"]:
        # Explicit R1 questions must not use generic G1 or company rules.
        if mentions_r1 and not rule["id"].startswith("r1_"):
            continue
        keyword_match = any(contains_term(question, term) for term in rule.get("keywords", []))
        recognized_keyword |= keyword_match
        subjects = rule.get("subjects", [])
        subject_match = not subjects or any(contains_term(question, term) for term in subjects)
        exact_question = any(key == question_key(text) for text in rule.get("questions", []))
        if (rule["id"].startswith("company_") and company_reference and not named_company
                and not exact_question and not is_generic_company_product_question(question, subjects)):
            # Never use Auto Didactic's product listing to answer about another
            # named or ambiguous company, even if that brand is in our catalog.
            continue
        if exact_question or (keyword_match and subject_match):
            matches.append(rule)

    if not matches:
        answer = CANNOT_ANSWER if known_topic or recognized_keyword else NOT_UNDERSTOOD
        return KeywordDecision("protected" if protected_topic else "unmatched", answer)
    priority = max(rule.get("priority", 0) for rule in matches)
    selected = [rule for rule in matches if rule.get("priority", 0) == priority]
    answers = {rule["answer"].strip() for rule in selected}
    # Do not choose an arbitrary intent when several different answers match.
    if len(answers) != 1:
        return KeywordDecision("protected", NOT_UNDERSTOOD, tuple(rule["id"] for rule in selected))
    return KeywordDecision("prepared", answers.pop(), tuple(rule["id"] for rule in selected))


def answer_from_keywords(message: str) -> str:
    return classify_keyword_reply(message).answer
