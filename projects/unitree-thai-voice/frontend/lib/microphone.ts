export type MicrophoneSession = { start(): Promise<void>; stop(): void; abort(): void };

export type MicrophoneInput = { deviceId: string; label: string };
const INPUT_PREFERENCE = "g1-microphone-device";

export function getPreferredMicrophone(): string {
  try { return window.localStorage.getItem(INPUT_PREFERENCE) ?? ""; }
  catch { return ""; }
}

export function setPreferredMicrophone(deviceId: string) {
  try { window.localStorage.setItem(INPUT_PREFERENCE, deviceId); }
  catch { /* The selected input still works when storage is unavailable. */ }
}

export function createSilenceDetector(startedAt: number) {
  let lastVoiceAt = startedAt;
  let heardVoice = false;
  return (level: number, now: number): "listening" | "silence" | "empty" | "limit" => {
    if (level >= 0.008) {
      heardVoice = true;
      lastVoiceAt = now;
    }
    if (now - startedAt >= 60_000) return "limit";
    if (!heardVoice && now - startedAt >= 12_000) return "empty";
    if (heardVoice && now - lastVoiceAt >= 1600) return "silence";
    return "listening";
  };
}

export function createMicrophoneSession(callbacks: {
  onStart(): void;
  onStopping(): void;
  onComplete(blob: Blob, extension: string): void;
  onError(message: string): void;
  onInput?(input: MicrophoneInput): void;
  onLevel?(level: number): void;
}, options: { deviceId?: string; autoStop?: boolean } = {}): MicrophoneSession {
  let stream: MediaStream | null = null;
  let context: AudioContext | null = null;
  let recorder: MediaRecorder | null = null;
  let poll: ReturnType<typeof setInterval> | undefined;
  let tail: ReturnType<typeof setTimeout> | undefined;
  let finished = false;
  let stopping = false;

  function cleanup() {
    clearInterval(poll);
    clearTimeout(tail);
    if (recorder) {
      recorder.onstop = null;
      recorder.onerror = null;
      if (recorder.state !== "inactive") recorder.stop();
    }
    stream?.getTracks().forEach((track) => track.stop());
    if (context) void context.close().catch(() => {});
  }

  function fail(message: string) {
    if (finished) return;
    finished = true;
    cleanup();
    callbacks.onError(message);
  }

  function stop() {
    if (finished || stopping || !recorder) return;
    stopping = true;
    clearInterval(poll);
    callbacks.onStopping();
    tail = setTimeout(() => {
      if (recorder?.state === "recording") recorder.stop();
    }, 250);
  }

  return {
    async start() {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
        fail("ไม่สามารถเปิดไมค์ได้ กรุณาใช้ Chrome ผ่าน localhost หรือ HTTPS");
        return;
      }
      try {
        // Resume in the click handler so browser audio activation is available.
        context = new AudioContext();
        await context.resume();
        if (finished) { cleanup(); return; }
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            deviceId: options.deviceId ? { exact: options.deviceId } : undefined,
            channelCount: 1,
            // Keep the input waveform for transcription. Browser call effects
            // can gate syllables or boost clicks on a laptop microphone. The
            // conversation page pauses answer audio before it opens the mic.
            echoCancellation: false, noiseSuppression: false, autoGainControl: false,
          },
        });
        if (finished) { cleanup(); return; }
        const input = stream.getAudioTracks()[0];
        callbacks.onInput?.({ deviceId: input.getSettings().deviceId ?? "", label: input.label });

        const analyser = context.createAnalyser();
        analyser.fftSize = 2048;
        context.createMediaStreamSource(stream).connect(analyser);
        const samples = new Float32Array(analyser.fftSize);
        const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
          .find((type) => MediaRecorder.isTypeSupported(type));
        recorder = new MediaRecorder(stream, { ...(mimeType ? { mimeType } : {}), audioBitsPerSecond: 128000 });
        const mime = recorder.mimeType;
        const extension = mime.includes("mp4") ? "mp4" : mime.includes("ogg") ? "ogg" : "webm";
        const chunks: Blob[] = [];
        recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
        recorder.onerror = () => fail("รับเสียงจากไมค์ไม่สำเร็จ กรุณาลองใหม่");
        recorder.onstop = () => {
          if (finished) return;
          // onstop follows the final dataavailable event; keep all audio chunks.
          const blob = new Blob(chunks, { type: mime });
          finished = true;
          cleanup();
          if (blob.size) callbacks.onComplete(blob, extension);
          else callbacks.onError("ยังไม่ได้รับเสียง กรุณากดไมค์แล้วพูดใหม่");
        };
        recorder.onstart = () => {
          if (finished) return;
          callbacks.onStart();
          const detect = createSilenceDetector(performance.now());
          poll = setInterval(() => {
            analyser.getFloatTimeDomainData(samples);
            let energy = 0;
            for (const sample of samples) energy += sample * sample;
            const level = Math.sqrt(energy / samples.length);
            callbacks.onLevel?.(level);
            const state = detect(level, performance.now());
            if (state === "limit") stop();
            else if (options.autoStop !== false) {
              if (state === "empty") fail("ยังไม่ได้ยินคำถาม กดไมค์แล้วพูดอีกครั้ง");
              else if (state === "silence") stop();
            }
          }, 80);
        };
        recorder.start(250);
      } catch (error) {
        const denied = error instanceof DOMException && error.name === "NotAllowedError";
        const missing = error instanceof DOMException && ["NotFoundError", "OverconstrainedError"].includes(error.name);
        fail(denied ? "กรุณาอนุญาตไมโครโฟนในเบราว์เซอร์แล้วกดใหม่"
          : missing ? "ไม่พบไมค์ที่เลือก กรุณาเลือกอุปกรณ์ใหม่ในหน้าทดสอบไมค์"
          : "เปิดไมค์ไม่สำเร็จ กรุณาตรวจไมโครโฟนแล้วลองใหม่");
      }
    },
    stop,
    abort() { finished = true; cleanup(); },
  };
}
