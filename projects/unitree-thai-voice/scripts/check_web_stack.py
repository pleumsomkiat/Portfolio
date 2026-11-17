"""Exercise the web proxy, local STT, configured replies and TTS without robot output."""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from time import perf_counter
from urllib.parse import urljoin

import httpx


def normalize_transcript(text: str) -> str:
    # Keep Thai vowels and tone marks; ignore only spacing and punctuation.
    return "".join(
        char for char in text.casefold()
        if unicodedata.category(char)[0] in {"L", "M", "N"}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--audio", type=Path, help="WAV, WebM, MP4 or OGG speech sample")
    parser.add_argument("--expected-text", help="Expected transcription, ignoring spacing and punctuation")
    parser.add_argument("--question", default="บริษัท ออโต ไดแด็กติก ก่อตั้งเมื่อไหร่")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.expected_text and not args.audio:
        parser.error("--expected-text requires --audio")
    base_url = args.base_url.rstrip("/")
    report: dict = {}

    with httpx.Client(timeout=180, trust_env=False) as client:
        health = client.get(f"{args.backend_url.rstrip('/')}/health")
        health.raise_for_status()
        report["health"] = health.json()
        if report["health"]["robot_audio_enabled"]:
            raise RuntimeError("ปิด ROBOT_AUDIO_ENABLED ก่อนทดสอบเว็บโดยไม่ส่งเสียงไปหุ่นยนต์")

        page = client.get(base_url)
        page.raise_for_status()
        if "UNITREE" not in page.text:
            raise RuntimeError("หน้าเว็บไม่ใช่ Unitree G1")
        report["web_status"] = page.status_code
        print("[PASS] หน้าเว็บและ health endpoint", flush=True)

        question = args.question
        if args.audio:
            started = perf_counter()
            with args.audio.open("rb") as source:
                response = client.post(f"{base_url}/api/transcribe", files={
                    "file": (args.audio.name, source, "application/octet-stream"),
                })
            response.raise_for_status()
            question = response.json()["text"].strip()
            if not question:
                raise RuntimeError("ถอดเสียงแล้วไม่มีข้อความ")
            report["transcribe_seconds"] = round(perf_counter() - started, 2)
            print(f"[PASS] Whisper: {question}", flush=True)
            if args.expected_text:
                report["expected_text"] = args.expected_text
                report["transcription_matches"] = normalize_transcript(question) == normalize_transcript(args.expected_text)
                if not report["transcription_matches"]:
                    raise RuntimeError(f"คำถอดเสียงไม่ตรงกับประโยคอ้างอิง: {args.expected_text}")

        report["question"] = question
        started = perf_counter()
        response = client.post(f"{base_url}/api/chat", json={"message": question, "speak": True})
        response.raise_for_status()
        result = response.json()
        report["chat_seconds"] = round(perf_counter() - started, 2)
        report["chat"] = result
        if not result["answer"].strip():
            raise RuntimeError("AI ไม่ส่งคำตอบ")
        print(f"[PASS] คำตอบ: {result['answer']}", flush=True)
        if not result.get("audio_url"):
            raise RuntimeError(f"ไม่มีไฟล์เสียงตอบกลับ: {result['audio_status']}")

        response = client.get(urljoin(base_url + "/", result["audio_url"]))
        response.raise_for_status()
        if not response.content or not response.headers.get("content-type", "").startswith("audio/"):
            raise RuntimeError("ไฟล์เสียงตอบกลับว่างหรือชนิดข้อมูลไม่ถูกต้อง")
        report["audio_bytes"] = len(response.content)
        print(f"[PASS] โหลดเสียงผ่านเว็บ: {len(response.content)} bytes", flush=True)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ผ่านการทดสอบเว็บ → คำตอบ → TTS" + (" พร้อมถอดเสียง" if args.audio else ""), flush=True)


if __name__ == "__main__":
    main()
