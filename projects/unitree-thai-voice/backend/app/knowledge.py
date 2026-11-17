from pathlib import Path
import re

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"

KEYWORDS = [
    "unitree", "g1", "r1", "หุ่นยนต์", "ภาษาไทย",
    "เสียง", "ลำโพง", "ไมโครโฟน", "ไมค์",
    "พูด", "สนทนา", "เว็บไซต์", "เว็บ",
    "ขนาด", "สูง", "น้ำหนัก", "แบตเตอรี่",
    "เดิน", "เคลื่อนไหว", "ชื่อ", "sdk2",
    "autodidactic", "บริษัท", "ประวัติ", "ก่อตั้ง", "ธุรกิจ",
    "สินค้า", "ขาย", "จำหน่าย", "ผลิตภัณฑ์", "บริการ", "อบรม",
    "ติดต่อ", "ที่อยู่", "อยู่ที่ไหน", "โทร", "เบอร์", "อีเมล",
    "ราคา", "ใบเสนอราคา", "สต็อก", "รับประกัน", "เวลาทำการ",
    "company", "history", "founded", "product", "service", "training",
    "contact", "address", "phone",
    "dobot", "hanback", "automation studio", "aiot",
    "นิวแมติก", "ไฮดรอลิก", "แมคคาทรอนิก", "พลังงานทดแทน",
]

COMPANY_ALIASES = (
    "ออโต ไดแด็กติก", "ออโตไดแด็กติก",
    "ออโต้ ไดแด็กติก", "ออโต้ไดแด็กติก",
    "ออโต ไดแดคติก", "ออโตไดแดคติก",
    "auto didactic", "auto-didactic",
)

# Entity names identify a subject, but should not outrank the requested fact.
GENERAL_KEYWORDS = {"unitree", "g1", "r1", "หุ่นยนต์", "autodidactic", "บริษัท"}
KEYWORD_ALIASES = {
    "น้ำหนัก": ("น้ำหนัก", "หนัก", "weight"),
    "สูง": ("สูง", "height"),
    "แบตเตอรี่": ("แบตเตอรี่", "แบต", "battery"),
    "อีเมล": ("อีเมล", "อีเมล์", "email", "e-mail", "e mail"),
}


def contains_keyword(text: str, keyword: str) -> bool:
    return any(alias in text for alias in KEYWORD_ALIASES.get(keyword, (keyword,)))


def normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    normalized = re.sub(r"(?<![a-z0-9])r\s+1(?![a-z0-9])", "r1", normalized)
    normalized = re.sub(r"อาร์\s*(?:วัน|หนึ่ง)", "r1", normalized)
    for alias in COMPANY_ALIASES:
        normalized = normalized.replace(alias, "autodidactic")
    return normalized

def load_documents():
    documents = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")

        sections = re.split(
            r"(?=^## )",
            content,
            flags=re.MULTILINE
        )

        for section in sections:
            section = section.strip()

            # A document title without body text is not a useful search result.
            if section and "\n" in section:
                documents.append({
                    "source": path.name,
                    "content": section,
                })

    return documents


def search_knowledge(question: str, limit: int = 3):
    question_lower = normalize_text(question)
    matches = []
    question_keywords = [
        keyword for keyword in KEYWORDS
        if contains_keyword(question_lower, keyword)
    ]
    preferred_source = ""
    mentions_r1 = re.search(r"(?<![a-z0-9])r1(?![a-z0-9])", question_lower) is not None
    if "autodidactic" in question_lower:
        preferred_source = "auto_didactic.md"
    elif mentions_r1:
        preferred_source = "unitree_r1.md"
    elif "unitree" in question_lower or "g1" in question_lower:
        preferred_source = "unitree_g1.md"

    for doc in load_documents():
        if mentions_r1 and doc["source"] != "unitree_r1.md":
            continue
        if not mentions_r1 and doc["source"] == "unitree_r1.md":
            continue
        content_lower = normalize_text(doc["content"])
        heading = normalize_text(doc["content"].splitlines()[0])
        score = 0

        for keyword in question_keywords:
            if contains_keyword(content_lower, keyword):
                if keyword in GENERAL_KEYWORDS:
                    score += 1
                else:
                    score += 4
                    if contains_keyword(heading, keyword):
                        score += 2

        if score > 0:
            matches.append((score, doc["source"] == preferred_source, doc))

    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)

    return [doc for _, _, doc in matches[:limit]]


def build_knowledge_context(question: str):
    results = search_knowledge(question)

    if not results:
        return ""

    return "\n\n".join(
        f"แหล่งข้อมูล: {item['source']}\n{item['content']}"
        for item in results
    )
