"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "../theme-provider";
import {
  createMicrophoneSession, getPreferredMicrophone, setPreferredMicrophone,
  type MicrophoneSession,
} from "../../lib/microphone";
import styles from "./microphone.module.css";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
type Phase = "idle" | "starting" | "recording" | "stopping" | "transcribing";

export default function MicrophoneTest() {
  const { theme, setTheme } = useTheme();
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selected, setSelected] = useState("");
  const [inputLabel, setInputLabel] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [level, setLevel] = useState(0);
  const [status, setStatus] = useState("เลือกไมค์ แล้วกดเริ่มทดสอบ");
  const [text, setText] = useState("");
  const sessionRef = useRef<MicrophoneSession | null>(null);
  const requestRef = useRef<AbortController | null>(null);

  async function refreshDevices() {
    try {
      const available = await navigator.mediaDevices?.enumerateDevices();
      setDevices((available ?? []).filter(device => device.kind === "audioinput"
        && !["default", "communications"].includes(device.deviceId)));
    } catch {
      setStatus("อ่านรายชื่อไมค์ไม่ได้ กรุณาเปิดผ่าน localhost หรือ HTTPS");
    }
  }

  useEffect(() => {
    setSelected(getPreferredMicrophone());
    void refreshDevices();
    const media = navigator.mediaDevices;
    const refresh = () => { void refreshDevices(); };
    media?.addEventListener("devicechange", refresh);
    return () => {
      media?.removeEventListener("devicechange", refresh);
      sessionRef.current?.abort();
      requestRef.current?.abort();
    };
  }, []);

  async function transcribe(blob: Blob, extension: string) {
    sessionRef.current = null;
    setPhase("transcribing");
    setLevel(0);
    setStatus("กำลังถอดเสียง...");
    const controller = new AbortController();
    requestRef.current = controller;
    try {
      const form = new FormData();
      form.append("file", blob, `question.${extension}`);
      const response = await fetch(`${API_BASE}/api/transcribe`, {
        method: "POST", body: form, signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "ถอดเสียงไม่สำเร็จ");
      setText(String(result.text ?? ""));
      setStatus("ถอดเสียงแล้ว ลองเทียบข้อความกับประโยคที่พูด");
    } catch (error) {
      if (controller.signal.aborted) return;
      setStatus(error instanceof Error ? error.message : "ถอดเสียงไม่สำเร็จ");
    } finally {
      if (!controller.signal.aborted) setPhase("idle");
    }
  }

  function toggleRecording() {
    if (sessionRef.current) {
      sessionRef.current.stop();
      return;
    }
    if (phase !== "idle") return;
    setText("");
    setInputLabel("");
    setPhase("starting");
    setStatus("กำลังเปิดไมค์ รอข้อความว่าพร้อมก่อนเริ่มพูด");
    const session = createMicrophoneSession({
      onInput(input) {
        setInputLabel(input.label || "ไมโครโฟนที่เบราว์เซอร์เลือก");
        void refreshDevices();
      },
      onLevel(value) {
        setLevel(Math.max(0, Math.min(100, (20 * Math.log10(Math.max(value, 0.00001)) + 60) / 60 * 100)));
      },
      onStart() {
        setPhase("recording");
        setStatus("พร้อมแล้ว พูดประโยคสั้น ๆ แล้วกดหยุดและถอดเสียง");
      },
      onStopping() { setPhase("stopping"); setStatus("กำลังเก็บท้ายเสียง..."); },
      onComplete(blob, extension) { void transcribe(blob, extension); },
      onError(message) {
        sessionRef.current = null;
        setPhase("idle");
        setLevel(0);
        setStatus(message);
      },
    }, { deviceId: selected, autoStop: false });
    sessionRef.current = session;
    void session.start();
  }

  return (
    <main className={styles.page}>
      <a href="/" className={styles.back}>← กลับไปสนทนากับ G1</a>
      <header className={styles.header}>
        <p>UNITREE G1</p>
        <h1>การตั้งค่า</h1>
        <p>ปรับรูปแบบการแสดงผลและเลือกไมโครโฟนที่ใช้สนทนา</p>
      </header>
      <section className={styles.card} aria-labelledby="appearance-title">
        <h2 id="appearance-title">รูปแบบการแสดงผล</h2>
        <div className={styles.themeOptions} role="group" aria-label="เลือกโหมดการแสดงผล">
          <button type="button" className={styles.themeOption} aria-pressed={theme === "light"}
            onClick={() => setTheme("light")}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" />
            </svg>
            กลางวัน
          </button>
          <button type="button" className={styles.themeOption} aria-pressed={theme === "dark"}
            onClick={() => setTheme("dark")}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z" />
            </svg>
            กลางคืน
          </button>
        </div>
        <p className={styles.hint}>ระบบจะจำโหมดที่เลือกไว้สำหรับครั้งถัดไป</p>
      </section>
      <section className={styles.card} aria-labelledby="microphone-title">
        <h2 id="microphone-title">เลือกและทดสอบไมโครโฟน</h2>
        <label htmlFor="microphone-input">ไมโครโฟนที่ใช้</label>
        <select id="microphone-input" value={selected} disabled={phase !== "idle"}
          onChange={event => { setSelected(event.target.value); setPreferredMicrophone(event.target.value); }}>
          <option value="">ใช้ไมค์เริ่มต้นของระบบ</option>
          {selected && !devices.some(device => device.deviceId === selected)
            && <option value={selected}>ไมค์ที่เคยเลือก (ยังไม่พบอุปกรณ์)</option>}
          {devices.map((device, index) => <option key={device.deviceId} value={device.deviceId}>
            {device.label || `ไมโครโฟน ${index + 1}`}
          </option>)}
        </select>
        <p className={styles.hint}>หากยังไม่เห็นชื่ออุปกรณ์ ให้กดเริ่มและอนุญาตไมค์ก่อน ไมค์ที่เลือกจะใช้ในหน้าสนทนาด้วย</p>
        <label htmlFor="input-level">ระดับเสียง — แถบควรขยับเมื่อพูด</label>
        <meter id="input-level" min={0} max={100} value={level} />
        {inputLabel && <p className={styles.hint}>อุปกรณ์ที่รับเสียง: {inputLabel}</p>}
        <button type="button" className={phase === "recording" ? styles.recording : ""}
          disabled={["starting", "stopping", "transcribing"].includes(phase)} onClick={toggleRecording}>
          {phase === "recording" ? "หยุดและถอดเสียง" : "เริ่มทดสอบไมค์"}
        </button>
        <p className={styles.status} role="status">{status}</p>
      </section>
      <section className={styles.card} aria-labelledby="transcript-title">
        <h2 id="transcript-title">ข้อความที่ระบบได้ยิน</h2>
        <p className={styles.transcript} aria-live="polite">{text || "ยังไม่มีข้อความที่ถอดได้"}</p>
      </section>
      <p className={styles.hint}>หน้านี้ทดสอบการรับและถอดเสียง โดยไม่ส่งคำถามไปให้ AI ตอบ เสียงไมค์ไม่ถูกบันทึกเป็นไฟล์บนเซิร์ฟเวอร์</p>
    </main>
  );
}
