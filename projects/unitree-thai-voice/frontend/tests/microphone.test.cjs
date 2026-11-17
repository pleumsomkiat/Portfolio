const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "../lib/microphone.ts"), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: {
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
} }).outputText;

function setup({ unavailable = false } = {}) {
  const requests = [], inputs = [], errors = [], completed = [];
  const intervals = new Set(), timers = new Set();
  let now = 0, stopped = false, recorder;
  const track = { stop() { stopped = true; }, label: "USB microphone",
    getSettings() { return { deviceId: "usb-mic" }; } };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  class Recorder {
    static isTypeSupported(type) { return type.startsWith("audio/webm"); }
    constructor(input, options) { this.state = "inactive"; this.mimeType = options.mimeType; recorder = this; }
    start() { this.state = "recording"; this.onstart?.(); }
    stop() {
      this.state = "inactive";
      this.ondataavailable?.({ data: new Blob(["end"]) });
      this.onstop?.();
    }
  }
  class Context {
    resume() { return Promise.resolve(); }
    close() { return Promise.resolve(); }
    createAnalyser() { return { fftSize: 2048, getFloatTimeDomainData(samples) { samples.fill(0); } }; }
    createMediaStreamSource() { return { connect() {} }; }
  }
  const exports = {};
  vm.runInNewContext(compiled, {
    exports, Blob, DOMException, AudioContext: Context, MediaRecorder: Recorder,
    navigator: { mediaDevices: { async getUserMedia(options) {
      requests.push(options);
      if (unavailable) throw new DOMException("Disconnected", "OverconstrainedError");
      return stream;
    } } },
    performance: { now: () => now },
    setInterval(fn) { intervals.add(fn); return fn; }, clearInterval(fn) { intervals.delete(fn); },
    setTimeout(fn) { timers.add(fn); return fn; }, clearTimeout(fn) { timers.delete(fn); },
  });
  const callbacks = {
    onStart() {}, onStopping() {}, onInput(input) { inputs.push(input); },
    onError(message) { errors.push(message); }, onComplete(blob) { completed.push(blob); },
  };
  return { api: exports, requests, inputs, errors, completed, callbacks,
    recorder: () => recorder, stopped: () => stopped,
    tick(time) { now = time; for (const fn of [...intervals]) fn(); },
    flushTail() { for (const fn of [...timers]) { timers.delete(fn); fn(); } },
  };
}

test("selected microphone is used and the final audio chunk is kept", async () => {
  const env = setup();
  const session = env.api.createMicrophoneSession(env.callbacks, { deviceId: "usb-mic" });
  await session.start();
  assert.equal(env.requests[0].audio.deviceId.exact, "usb-mic");
  assert.equal(env.inputs[0].label, "USB microphone");
  env.recorder().ondataavailable({ data: new Blob(["start-"]) });
  session.stop();
  env.flushTail();
  assert.equal(await env.completed[0].text(), "start-end");
  assert.equal(env.stopped(), true);
});

test("diagnostic recording waits for manual stop even without detected sound", async () => {
  const env = setup();
  const session = env.api.createMicrophoneSession(env.callbacks, { autoStop: false });
  await session.start();
  env.tick(13000);
  assert.equal(env.recorder().state, "recording");
  assert.deepEqual(env.errors, []);
  session.stop();
  env.flushTail();
  assert.equal(env.completed.length, 1);
});

test("normal recording still closes an unused microphone", async () => {
  const env = setup();
  const session = env.api.createMicrophoneSession(env.callbacks);
  await session.start();
  env.tick(13000);
  assert.equal(env.errors.length, 1);
  assert.equal(env.completed.length, 0);
  assert.equal(env.stopped(), true);
});

test("a disconnected selected device is reported instead of choosing another input", async () => {
  const env = setup({ unavailable: true });
  const session = env.api.createMicrophoneSession(env.callbacks, { deviceId: "usb-mic" });
  await session.start();
  assert.equal(env.requests.length, 1);
  assert.match(env.errors[0], /ไม่พบไมค์ที่เลือก/);
});
