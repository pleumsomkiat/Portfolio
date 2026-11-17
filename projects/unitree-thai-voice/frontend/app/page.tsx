"use client";

import { useEffect, useRef, useState } from "react";
import { createMicrophoneSession, getPreferredMicrophone, type MicrophoneSession } from "../lib/microphone";
import styles from "./voice.module.css";

type Message = { role: "user" | "assistant"; text: string; audioUrl?: string };
type ChatResponse = {
  answer: string;
  audio_url: string | null;
  audio_status: string;
  robot_status: string;
};

// Use the web server's proxy so phones never call their own localhost:8000.
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [listening, setListening] = useState(false);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [status, setStatus] = useState("พร้อมสนทนา");
  const [inputLabel, setInputLabel] = useState("");
  const [inputLevel, setInputLevel] = useState(0);
  const [inputError, setInputError] = useState<string | null>(null);
  const sessionRef = useRef<MicrophoneSession | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const busyRef = useRef(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy, listening, inputError]);

  useEffect(() => () => {
    sessionRef.current?.abort();
    sessionRef.current = null;
    audioRef.current?.pause();
  }, []);

  async function playAnswer(url: string) {
    const previous = audioRef.current;
    if (previous) {
      previous.onended = null;
      previous.onerror = null;
      previous.pause();
    }

    const audio = new Audio(url);
    audioRef.current = audio;
    setSpeaking(true);
    setStatus("G1 กำลังพูด...");
    audio.onended = () => {
      if (audioRef.current !== audio) return;
      setSpeaking(false);
      if (!sessionRef.current) setStatus("พร้อมรับคำถาม");
    };
    audio.onerror = () => {
      if (audioRef.current !== audio) return;
      setSpeaking(false);
      if (!sessionRef.current) setStatus("โหลดเสียงตอบกลับไม่สำเร็จ");
    };
    try { await audio.play(); }
    catch {
      if (audioRef.current !== audio || sessionRef.current) return;
      setSpeaking(false);
      setStatus("เลือกฟังคำตอบอีกครั้งเพื่อเล่นเสียง");
    }
  }

  async function transcribeAndAsk(blob: Blob, extension: string) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setStatus("กำลังอ่านคำถาม...");
    try {
      const form = new FormData();
      form.append("file", blob, `question.${extension}`);
      const response = await fetch(`${API_BASE}/api/transcribe`, { method: "POST", body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "รับคำถามไม่สำเร็จ");
      const text = String(data.text ?? "").trim();
      if (!text) throw new Error("ยังไม่ได้ยินคำถาม กรุณาลองใหม่");
      busyRef.current = false;
      await sendMessage(text);
    } catch (error) {
      const message = error instanceof Error ? error.message : "รับคำถามไม่สำเร็จ";
      setInputError(message);
      setStatus(message);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  async function sendMessage(text: string) {
    const message = text.trim();
    if (!message || busyRef.current) return;
    if (message.length > 2000) {
      setStatus("คำถามยาวเกินไป กรุณาถามครั้งละไม่เกิน 2,000 ตัวอักษร");
      return;
    }

    busyRef.current = true;
    setBusy(true);
    setMessages((old) => [...old, { role: "user", text: message }]);
    setStatus("G1 กำลังคิดคำตอบ...");

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, speak: true }),
      });
      const data = (await response.json()) as ChatResponse | { detail?: string };
      if (!response.ok || !("answer" in data)) {
        throw new Error("detail" in data ? data.detail ?? "AI ตอบกลับผิดพลาด" : "Backend ตอบกลับไม่ถูกต้อง");
      }

      const audioUrl = data.audio_url
        ? new URL(data.audio_url, API_BASE || window.location.origin).toString()
        : undefined;
      setMessages((old) => [...old, { role: "assistant", text: data.answer, audioUrl }]);
      audioRef.current?.pause();
      audioRef.current = null;
      setSpeaking(false);

      if (audioUrl) {
        await playAnswer(audioUrl);
      } else {
        setStatus(data.audio_status);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "เกิดข้อผิดพลาด");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  function toggleMicrophone() {
    if (busyRef.current) return;
    if (sessionRef.current) {
      sessionRef.current.stop();
      return;
    }

    audioRef.current?.pause();
    setSpeaking(false);
    setInputError(null);
    setInputLabel("");
    setInputLevel(0);
    setStarting(true);
    setStatus("กำลังเปิดไมค์...");

    const session = createMicrophoneSession({
      onInput(input) {
        setInputLabel(input.label || "ไมโครโฟนที่เบราว์เซอร์เลือก");
      },
      onLevel(level) {
        setInputLevel(Math.max(0, Math.min(100, (20 * Math.log10(Math.max(level, 0.00001)) + 60) / 60 * 100)));
      },
      onStart() {
        setStarting(false);
        setListening(true);
        setStatus("กำลังฟังคำถาม...");
      },
      onStopping() {
        setStopping(true);
        setStatus("กำลังส่งคำถาม...");
      },
      onComplete(blob, extension) {
        sessionRef.current = null;
        setListening(false);
        setStarting(false);
        setStopping(false);
        setInputLevel(0);
        void transcribeAndAsk(blob, extension);
      },
      onError(message) {
        sessionRef.current = null;
        setListening(false);
        setStarting(false);
        setStopping(false);
        setInputLevel(0);
        setInputError(message);
        setStatus(message);
      },
    }, { deviceId: getPreferredMicrophone() });
    sessionRef.current = session;
    void session.start();
  }

  return (
    <main className={styles.page}>
      <section className={styles.console} aria-label="Unitree G1 Thai Voice Assistant">
        <header className={styles.topbar}>
          <div className={styles.brand}>
            <h1>UNITREE <span>G1</span></h1>
            <span className={styles.brandDivider} aria-hidden="true" />
            <p>THAI VOICE ASSISTANT</p>
          </div>
          <div className={styles.vent} aria-hidden="true"><i /><i /><i /></div>
        </header>

        <div className={styles.content}>
        <section className={styles.chatPanel} aria-labelledby="conversation-title">
          <header className={styles.chatHeader}>
            <h2 id="conversation-title">บทสนทนา</h2>
            <a href="/microphone" className={styles.micSettings}>การตั้งค่า</a>
          </header>
          <div className={styles.messages} role="log" aria-label="บทสนทนากับ G1" aria-live="polite">
            {messages.length === 0 && !listening && !busy && !inputError && (
              <div className={styles.empty}>
                <span className={styles.emptyAvatar} aria-hidden="true" />
                <h3>เริ่มบทสนทนากับ G1</h3>
                <p>ผู้ช่วยของคุณ พร้อมพูดคุยภาษาไทย</p>
              </div>
            )}
            {messages.map((message, index) => (
              <div key={index} className={`${styles.messageRow} ${message.role === "user" ? styles.userRow : styles.aiRow}`}>
                {message.role === "assistant" && <span className={styles.avatar} aria-hidden="true" />}
                <div className={styles.messageContent}>
                <div className={message.role === "user" ? styles.userMessage : styles.aiMessage}>
                <strong className={styles.srOnly}>{message.role === "user" ? "คุณ" : "G1"}</strong>
                <p>{message.text}</p>
                </div>
                {message.audioUrl && (
                  <button type="button" className={styles.replay}
                    disabled={listening || starting || stopping || busy}
                    onClick={() => void playAnswer(message.audioUrl!)}>
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" />
                      <path d="m10 8 6 4-6 4Z" fill="currentColor" stroke="none" />
                    </svg>
                    ฟังคำตอบอีกครั้ง
                  </button>
                )}
                </div>
              </div>
            ))}
            {inputError && (
              <div className={styles.inputError} role="alert">
                <strong>รับคำถามไม่สำเร็จ</strong>
                <p>{inputError}</p>
                <p>กดไมค์แล้วพูดใหม่ หรือ <a href="/microphone">การตั้งค่า</a></p>
              </div>
            )}
            {(listening || busy) && (
              <div className={styles.activity}>
                <span className={styles.avatar} aria-hidden="true" />
                <div className={`${styles.activityBubble} ${listening ? styles.listeningBubble : ""}`}>
                  <div className={styles.activityLabel}>
                    <span className={styles.dots} aria-hidden="true"><i /><i /><i /></span>
                    <span>{listening ? "กำลังฟังคำถาม" : "กำลังประมวลผล"}</span>
                  </div>
                  {listening && <>
                    <p className={styles.inputLabel}>ไมค์: {inputLabel || "กำลังตรวจอุปกรณ์..."}</p>
                    <meter className={styles.inputLevel} aria-label="ระดับเสียงไมโครโฟน" min={0} max={100} value={inputLevel} />
                    <p className={styles.inputLabel}>แถบระดับเสียงควรขยับเมื่อพูด</p>
                  </>}
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        </section>

        <aside className={`${styles.voicePanel} ${speaking ? styles.speaking : ""}`} aria-label="สนทนาด้วยเสียง">
          <svg className={styles.panelTrace} viewBox="0 0 400 600" preserveAspectRatio="none" aria-hidden="true">
            <path d="M0 130 64 116 144 0M400 80 325 96 280 144M0 500 42 540H358L400 500" />
          </svg>
          <img className={styles.robotPortrait} src="/images/g1-portrait.png" alt="Unitree G1" width={1280} height={1280} />
          <div className={styles.voiceControls}>
          <div className={`${styles.micRing} ${listening ? styles.listening : ""}`}>
          <button type="button"
            className={`${styles.micButton} ${listening ? styles.active : ""}`}
            onClick={toggleMicrophone} disabled={busy || starting || stopping}
            aria-label={listening ? "ส่งคำถามทันที" : "เริ่มพูดคำถาม"}
            aria-pressed={listening}>
            <svg viewBox="0 0 24 24" width="84" height="84" fill="none"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
              strokeLinejoin="round" aria-hidden="true">
              <rect x="9" y="2" width="6" height="13" rx="3" />
              <path d="M5 10v2a7 7 0 0 0 14 0v-2" />
              <path d="M12 19v3M8 22h8" />
            </svg>
          </button>
          </div>
          <div className={styles.voiceStatus}>
            <span className={`${styles.statusLight} ${listening || speaking ? styles.lit : ""}`} aria-hidden="true" />
            <p className={styles.status} role="status">{status}</p>
          </div>
          </div>
        </aside>
        </div>
      </section>
    </main>
  );
}
