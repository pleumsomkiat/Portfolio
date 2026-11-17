# Unitree G1 Thai Web Chatbot

เป้าหมายที่ผู้ใช้ยืนยัน: เพิ่มการสนทนาภาษาไทยให้ **G1 รุ่นปกติ** ที่ใช้แอป
**Unitree Explore** โดยเสียงตอบต้องออกจากลำโพงในตัวหุ่น. เว็บ/AI/TTS บนคอม
เป็นส่วนเสริมของประสบการณ์แอปเดิม. ช่องทางส่งเสียงผ่านโปรโตคอลของแอป
ยังอยู่ระหว่างตรวจสอบกับรุ่นและเฟิร์มแวร์จริง; ยังไม่ยืนยันว่า SDK2 bridge
ที่มีอยู่ใช้กับหุ่นตัวนี้ได้ และยังไม่ได้ส่งคำสั่งเสียงไปหุ่นจริง.

เว็บแชตบอตภาษาไทยที่แยกส่วนรับผิดชอบชัดเจน: หน้าเว็บ Next.js, API FastAPI, TTS ภายนอก และตัวส่งเสียง C++ ไปยัง Unitree SDK2. โปรเจกต์นี้ **ไม่มีโค้ดควบคุมการเคลื่อนไหว** และ `ROBOT_AUDIO_ENABLED=false` เป็นค่าเริ่มต้น จึงจะไม่ส่งคำสั่งใด ๆ ไปยังหุ่นยนต์ระหว่างพัฒนาและทดสอบเว็บ

> ข้อกำหนดบังคับ: ใช้ **Ubuntu 22.04 LTS และ Python 3.10 เท่านั้น** สำหรับโปรเจกต์นี้. ห้ามรันจากดิสโทร `Ubuntu` ที่เป็น 26.04 แม้จะมีอยู่ใน WSL. ให้เรียก `Ubuntu-22.04` โดยตรงทุกครั้ง หรือเปลี่ยน default WSL เป็นดิสโทรนี้ก่อนเริ่มทำงาน. Build/รัน `robot_bridge` บน Ubuntu 22.04 native หรือคอมพิวเตอร์ Linux ที่ต่อ LAN เดียวกับ G1 ก่อน; อย่าถือว่า WSL2 ส่ง DDS multicast ถึงหุ่นได้.

## โครงสร้าง

```text
frontend/       Next.js: หน้าจอแชตและเล่นไฟล์เสียงใน browser
backend/        FastAPI: ถอดเสียง เลือกคำตอบ TTS และตัวเรียก bridge แบบ opt-in
robot_bridge/   C++/SDK2: ตรวจ WAV และส่ง PCM ไปยังลำโพง G1 เท่านั้น
scripts/        ตรวจเครื่องมือ เครือข่าย และทดสอบเส้นทางเว็บ/API
```

ผลทดสอบและงานค้างล่าสุด: [PROJECT_STATUS.md](PROJECT_STATUS.md)

## 1) เตรียม Ubuntu/WSL

เปิด Ubuntu 22.04 โดยเฉพาะจาก PowerShell ก่อน (ห้ามเปิด `wsl` เฉย ๆ ขณะที่ default ยังเป็น Ubuntu 26.04):

```powershell
wsl -d Ubuntu-22.04

# ทำครั้งเดียวได้ หากต้องการให้ `wsl` เปิด 22.04 เป็นค่าเริ่มต้น
wsl --set-default Ubuntu-22.04
```

จากนั้นรันใน Ubuntu 22.04 terminal. ระบบต้องรายงาน `Ubuntu 22.04.x LTS` และ `Python 3.10.x`:

```bash
. /etc/os-release && echo "$PRETTY_NAME"
python3 --version
bash scripts/check_environment.sh
```

ติดตั้ง build/Python/audio dependencies:

```bash
sudo apt update
sudo apt install -y \
  build-essential cmake git curl pkg-config ffmpeg \
  python3 python3-venv python3-dev python3-pip \
  libyaml-cpp-dev libeigen3-dev libboost-all-dev libfmt-dev

# ต้องเป็น Node.js 20.9 ขึ้นไป (แนะนำ LTS ล่าสุดจาก nvm/NodeSource)
node --version
npm --version

python3 --version
cmake --version
g++ --version
```

Next.js 16 ต้องใช้ Node.js 20.9 ขึ้นไป จึงไม่ควรใช้ Node เวอร์ชันเก่าจาก Ubuntu 22.04 repository. ติดตั้ง Node LTS ภายใน Ubuntu 22.04 ผ่าน nvm หรือ NodeSource ตามมาตรฐานองค์กรของคุณก่อนทำ `npm install`. Node ที่อยู่บน Windows PATH ไม่ใช่ Node ที่ติดตั้งใน Ubuntu.

จาก root ของ repository นี้ใน WSL:

```bash
cd /mnt/d/'Unitree G1 thaiver'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

cd frontend
npm install
cd ..
```

หาก PowerShell แจ้งว่า `npm.ps1` ถูกบล็อก ให้เรียก `npm.cmd` แทน (เช่น `npm.cmd install`, `npm.cmd run dev`).

## 2) ตั้งค่าคำตอบและ TTS

```bash
cp backend/.env.example backend/.env
```

เครื่องทดสอบนี้ใช้ `AI_PROVIDER=hybrid`, `HYBRID_AI_PROVIDER=ollama` และ
`OLLAMA_MODEL=qwen2.5:3b`: คำถามที่มีคำตอบเตรียมไว้ใช้ข้อมูลใน
`backend/knowledge/responses_th.json` ส่วนคำถามทั่วไปให้ Ollama ในเครื่องตอบ.
คำถามเกี่ยวกับบริษัท/G1 ที่ยังไม่มีข้อมูลหรือกำกวมจะไม่ส่งให้โมเดลเดาคำตอบ.
เปิด Ollama พร้อมโมเดลที่ตั้งไว้ก่อนเริ่มใช้งานโหมดนี้.

```dotenv
AI_PROVIDER=hybrid
HYBRID_AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

ค่าเริ่มต้นของโค้ดยังเป็น `AI_PROVIDER=keywords` สำหรับใช้เฉพาะคำตอบตายตัว
โดยไม่เรียก LLM. ทั้งสองโหมดไม่ต้องมี API key เมื่อใช้ Ollama.
ใช้ `TTS_PROVIDER=edge` สำหรับเสียงตอบ และปิดส่งเสียงไป G1 เป็นค่าเริ่มต้น.
Edge TTS ต้องใช้อินเทอร์เน็ตตอนสร้างเสียง. โมเดล Ollama ไม่ได้ค้นอินเทอร์เน็ตสด.

การตั้งค่า provider อื่นที่ยังรองรับ หากเปลี่ยนจากโหมดคีย์เวิร์ดเอง:

```dotenv
# OpenAI Responses API
AI_PROVIDER=openai
OPENAI_API_KEY=ใส่คีย์ของคุณเฉพาะใน backend/.env
OPENAI_MODEL=gpt-5.5

# หรือ Ollama ในเครื่อง
# AI_PROVIDER=ollama
# OLLAMA_BASE_URL=http://127.0.0.1:11434
# OLLAMA_MODEL=ชื่อโมเดลที่ติดตั้งแล้ว
```

ห้าม commit `backend/.env`. การเชื่อมต่อ OpenAI ใช้ `AsyncOpenAI` และ Responses API ตาม [เอกสาร Python ทางการ](https://developers.openai.com/api/reference/python).

### คีย์เวิร์ดและคำตอบที่เตรียมไว้

การถอดเสียงและการเลือกคำตอบแยกจากกัน: หน้าจอแสดงข้อความที่ Whisper ถอดได้
แล้วจึงใช้ข้อความนั้นจับคีย์เวิร์ด. การจับคีย์เวิร์ดไม่เขียนทับคำถามของผู้ใช้.
ส่วนความแม่นยำในการถอดคำพูดยังต้องตรวจด้วยไมค์จริง.

แก้ `backend/knowledge/responses_th.json` เพื่อเพิ่มคีย์เวิร์ดและคำตอบได้ทันที
โดยไม่ต้องรีสตาร์ต API. แต่ละ rule มี:

- `id`: ชื่อรายการที่ไม่ซ้ำกัน
- `keywords`: พบอย่างน้อยหนึ่งคำจึงพิจารณาคำตอบนี้
- `subjects`: ถ้ามี ต้องพบหัวข้อที่ระบุอย่างน้อยหนึ่งคำร่วมกับคีย์เวิร์ด
- `questions`: คำถามเต็มที่รองรับโดยตรง ไม่คิดช่องว่าง วรรคตอน และคำลงท้ายสุภาพ
- `answer`: คำตอบตายตัวที่จะส่งไปสร้างเสียง
- `priority`: ค่ามากมีลำดับสูงกว่า; ถ้าลำดับสูงสุดมีหลายคำตอบต่างกันจะตอบว่าไม่เข้าใจคำถาม

ตัวอย่างรายการ:

```json
{
  "id": "robot_height",
  "priority": 20,
  "subjects": ["g1", "จีวัน"],
  "keywords": ["สูง", "height"],
  "answer": "Unitree G1 มีความสูงประมาณ 132 เซนติเมตรครับ"
}
```

ในโหมด `keywords` หากไม่พบคีย์เวิร์ดที่รองรับ จะตอบ **ไม่เข้าใจคำถามครับ**.
หากรู้หัวข้อหรือคีย์เวิร์ดแต่ไม่มีคำตอบที่กำหนดไว้ จะตอบ **ขออภัยครับ ผมยังไม่ทราบคำตอบสำหรับคำถามนี้ครับ**.
ในโหมด `hybrid` คำถามทั่วไปที่ไม่ตรงรายการจะใช้ AI; ข้อมูลบริษัทและหุ่นยนต์
ที่ยังไม่ยืนยัน รวมถึงคำถามกำกวม จะยังคงใช้คำตอบแจ้งว่าไม่ทราบหรือไม่เข้าใจ.
`topics` ระบุหัวข้อที่ระบบรู้จัก และ `unavailable_keywords` ระบุข้อมูลที่ยังตอบไม่ได้.
ชื่อบริษัทลอย ๆ จะไม่ถูกเดาเป็นคำถามเรื่องประวัติบริษัท และข้อมูลบริษัทอื่น
จะไม่ถูกแทนด้วยข้อมูล Auto Didactic. คำตอบใน JSON ต้องปรับให้ตรงกับข้อมูล
อ้างอิงในไฟล์ Markdown เมื่อข้อมูลเปลี่ยน; คำตอบที่เตรียมไว้ในทั้งสองโหมด
ไม่ถูกสรุปหรือเขียนใหม่ด้วย AI. รายการใหม่ควรมี `source` หรือ `sources` และ `verified_at`
เพื่อเก็บที่มาและวันที่ตรวจสอบ โดยเฉพาะชื่อผู้บริหารและรายการสินค้า.

## 3) ทดสอบก่อนต่อหุ่นยนต์

หน้าต่างที่ 1:

```bash
source .venv/bin/activate
bash scripts/run_backend.sh --reload
```

หน้าต่างที่ 2:

```bash
bash scripts/run_frontend.sh
```

สคริปต์เปิด Next.js ด้วย Webpack และตรวจไฟล์ทุก 1 วินาที เพื่อให้การแก้ไฟล์
จาก Windows ใน `/mnt/d` ส่งถึงหน้าเว็บที่รันใน WSL. หากเปิดด้วย file watcher
ที่ไม่เห็นการแก้จาก Windows อาจยังได้ JavaScript รุ่นเก่าแม้ไฟล์ต้นฉบับเปลี่ยนแล้ว.

เปิด <http://localhost:3000> แล้วส่งข้อความภาษาไทย. API docs อยู่ที่ <http://localhost:8000/docs>. ทดสอบอัตโนมัติโดยไม่เรียก TTS, AI ภายนอก หรือหุ่นยนต์:

```bash
source .venv/bin/activate
python -m pytest -q backend/tests
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"สวัสดี G1","speak":false}'
```

เมื่อเปิด backend และหน้าเว็บแล้ว ตรวจเส้นทางเว็บ → AI → TTS ด้วยผู้ให้บริการ
ที่ตั้งค่าไว้จริงได้ โดยต้องปิด `ROBOT_AUDIO_ENABLED` ระหว่างการทดสอบนี้:

```bash
python scripts/check_web_stack.py --report .runtime/smoke-latest.json

# เพิ่มไฟล์คำถามเพื่อทดสอบ Whisper → AI → TTS ผ่าน proxy ของเว็บด้วย
python scripts/check_web_stack.py --audio /path/to/question.wav \
  --report .runtime/smoke-latest.json

# หากทราบข้อความอ้างอิง ตรวจคำถอดด้วย (ไม่คิดช่องว่างหรือเครื่องหมายวรรคตอน)
python scripts/check_web_stack.py --audio /path/to/question.wav \
  --expected-text "บริษัทมีอีเมลอะไร" --report .runtime/stt-email-smoke.json
```

สคริปต์ตรวจการตอบกลับและโหลดไฟล์เสียงได้ แต่ไม่ได้ตรวจว่าเบราว์เซอร์
อนุญาตไมค์หรือเล่นเสียงออกลำโพงได้จริง. การรันนี้เรียก AI/TTS จริงตาม
`backend/.env`; Edge TTS ต้องใช้อินเทอร์เน็ต. การทดสอบ `pytest` ข้างต้น
ตรวจการค้นฐานความรู้ ข้อมูลคำถาม และการคัดกรองเสียงโดยไม่เรียกบริการภายนอก.
ตรวจการเลือกไมค์และการเก็บท้ายเสียงด้วย `cd frontend && npm test`.

### กดไมค์เพื่อถาม

หน้าเว็บรับเสียงจากไมค์ และส่งคำถามอัตโนมัติหลังเงียบประมาณ 1.6 วินาที.
กดไมค์อีกครั้งเพื่อจบคำถามเองได้ ระบบเก็บท้ายเสียงเพิ่ม 0.25 วินาที.
ระบบถอดเสียงด้วย faster-whisper ในเครื่อง
ผ่าน `/api/transcribe` แล้วส่งข้อความไป `/api/chat` อัตโนมัติ.

ขอเสียงจากไมค์โดยปิด `echoCancellation`, `noiseSuppression` และ `autoGainControl`
ของเบราว์เซอร์ เพื่อส่งเสียงต้นฉบับเข้าตัวถอดข้อความ. หน้าสนทนาหยุดเสียงตอบก่อนเปิดไมค์.
ปรับค่านี้หลังพบว่าไฟล์จากไมค์คอมถูกตัวตรวจคำพูดปฏิเสธ; ผู้ใช้ทดสอบแล้วมีข้อความขึ้นอีกครั้ง.

หากคำถอดไม่ตรง ให้เปิด **ทดสอบ / เลือกไมค์** ในหัวข้อบทสนทนา หรือเข้า
<http://localhost:3000/microphone>. เลือกอุปกรณ์ กดเริ่ม พูดแล้วกดหยุดเอง
เพื่อเทียบประโยคที่พูดกับข้อความที่ถอดได้. มีแถบระดับเสียงและชื่ออุปกรณ์
ที่รับเสียงจริง; ไมค์ที่เลือกจะถูกจดจำในเบราว์เซอร์และใช้ในหน้าสนทนาด้วย.
หน้าทดสอบไม่ส่งคำถามต่อไปให้ AI.

หน้าสนทนาแสดงชื่อไมค์และแถบระดับเสียงระหว่างรับคำถาม หากถอดเสียงไม่สำเร็จ
จะแสดงข้อผิดพลาดในบทสนทนาพร้อมทางไปเลือกไมค์ใหม่. ทั้งหน้าสนทนาและหน้าทดสอบ
ใช้เสียงในหน่วยความจำระหว่างอัดและส่งถอดข้อความเท่านั้น ไม่เก็บคลิปไว้ฟังย้อนหลัง
และไม่มีปุ่มดาวน์โหลดเสียงไมค์.

เปิดผ่าน localhost หรือ HTTPS และอนุญาตไมโครโฟน. เสียงรับเข้าประมวลผลจาก
หน่วยความจำ ไม่บันทึกไฟล์เสียงไมค์ลงดิสก์. การตรวจความเงียบใช้ระดับเสียง
จึงอาจต้องกดไมค์เพื่อจบคำถามเองในห้องที่มีเสียงรบกวนต่อเนื่อง.
หนึ่งคำถามรับเสียงสูงสุด 60 วินาที; หากไม่ได้ยินเสียง 12 วินาทีจะปิดไมค์.

Backend โหลดโมเดลไว้ตั้งแต่เริ่มบริการ และใช้แคชในเครื่องก่อนเพื่อไม่ต้อง
ติดต่อบริการรับเสียงภายนอก. ครั้งแรกที่ยังไม่มีโมเดลต้องดาวน์โหลดก่อน.
เลือกโมเดลผ่าน `STT_MODEL` (ค่าเริ่มต้น `small`) และคำใบ้ผ่าน
`STT_INITIAL_PROMPT`. รีสตาร์ต backend เมื่อเปลี่ยนค่าเหล่านี้.

### เร่งการถอดเสียงด้วย NVIDIA GPU

ติดตั้งไลบรารีเสริมใน Ubuntu 22.04 / `.venv`:

```bash
python -m pip install -r backend/requirements-gpu.txt
```

ตั้งค่าใน `backend/.env` แล้วเปิด backend ด้วยสคริปต์:

```dotenv
STT_DEVICE=cuda
STT_COMPUTE_TYPE=int8_float16
STT_CPU_THREADS=0
```

```bash
bash scripts/run_backend.sh
```

`run_backend.sh` ใช้ `run_python.sh` เตรียมพาธ cuBLAS/cuDNN/NVRTC ของ `.venv`
ก่อนเปิด Python ตาม [การตั้งค่า GPU ของ faster-whisper](https://github.com/SYSTRAN/faster-whisper#gpu).
โมเดลจะถูกโหลดและอุ่น GPU ตอนเริ่มบริการ จึงไม่ทิ้งค่าเริ่มต้น CUDA ไปให้คำถามแรก.
บนเครื่องทดสอบ RTX 3050 คลิปสั้นสามคลิปใช้เวลาผ่านเว็บประมาณ 0.6–0.9 วินาที
จากเดิม CPU ประมาณ 5–6 วินาที โดยใช้โมเดลไทยและ beam size 5 เดิม.
ผลนี้ยังไม่รวมเวลารอจบคำพูดและ TTS; การรอเงียบ 1.6 วินาทีและเก็บท้าย 0.25 วินาทียังคงเดิม.

หากใช้เครื่องไม่มี NVIDIA GPU ให้ตั้ง `STT_DEVICE=cpu` และ `STT_COMPUTE_TYPE=int8`.
`STT_CPU_THREADS=0` ใช้ค่าที่ CTranslate2 เลือกให้ หรือกำหนดจำนวนเธรดเพื่อทดลองเทียบได้.
วัดเวลาโดยไม่เปลี่ยน `.env` ด้วย:

```bash
bash scripts/run_python.sh scripts/benchmark_stt.py --device cuda \
  --audio /path/to/question.webm --repeat 2 --report .runtime/stt-benchmark.json
```

สำหรับการสนทนาภาษาไทย ให้เตรียมโมเดลที่ฝึกภาษาไทยโดยเฉพาะก่อน:

```bash
python scripts/prepare_thai_stt.py
```

จากนั้นตั้งใน `backend/.env` และรีสตาร์ต backend:

```dotenv
STT_MODEL=.runtime/models/whisper-th-medium-ct2
STT_LANGUAGE=th
```

สคริปต์ดาวน์โหลดน้ำหนักประมาณ 1.53 GB และ tokenizer ไว้ใน `.runtime/models`
โดยตรึงเวอร์ชันไว้. ใช้น้ำหนักที่แปลงเป็น CTranslate2 จาก
[Thaweewat/whisper-th-medium-ct2](https://huggingface.co/Thaweewat/whisper-th-medium-ct2)
และ tokenizer ของ
[biodatlab/whisper-th-medium-combined](https://huggingface.co/biodatlab/whisper-th-medium-combined).
บนเครื่องทดสอบ โมเดลนี้ใช้ CPU int8 และใช้เวลาประมาณ 5–7 วินาทีต่อคลิปสั้น;
ต้องวัดกับไมค์จริงอีกครั้ง. พาธโมเดลแบบ relative อ้างอิงจาก root โปรเจกต์.
ระบบถอดข้อความโดยไม่สร้าง timestamp และลดการวนคำซ้ำ. ค่าว่างของ
`STT_INITIAL_PROMPT` หมายถึงไม่มีคำใบ้อัตโนมัติ เพื่อให้สนทนาได้ทั่วไป.
`STT_HOTWORDS` ใช้ช่วยสะกดชื่อเฉพาะ โดยไม่ใส่คำตอบหรือประโยคคำถามทั้งประโยค.
ค่าที่เทียบกับเสียงผู้ใช้ในวิดีโอ `20261111_145411.mp4` แล้วถอดชื่อได้ดีขึ้นคือ:

```dotenv
STT_HOTWORDS=G1, ยูนิทรี, ออโต ไดแด็กติก
```

ในเสียงทดสอบ 6 ช่วง ชื่อบริษัทที่เดิมถอดผิดทั้ง 3 ช่วงถอดได้ตรงขึ้น และชื่อที่เดิม
ขึ้นว่า Unity เปลี่ยนเป็น “ยูนิทรี”; คำถามทั่วไปที่ใช้เทียบ 4 คลิปยังได้ข้อความเดิม.
ผลนี้ใช้โมเดลไทยข้างต้น ไม่ใช่การรับรองความแม่นยำทุกประโยคหรือทุกไมโครโฟน.
การแสดงชื่อ จีวัน / จีหนึ่ง / G 1 จะใช้รูป G1;
ไม่มีการแทนข้อความระยะเวลา “กี่วัน” เป็นชื่อหุ่นยนต์. รีสตาร์ต backend หลังแก้ค่า.
คำถาม “G1 ทำอะไรได้บ้าง” มีคำตอบเกี่ยวกับตัวหุ่นแยกจาก “คุณทำอะไรได้บ้าง”
ที่ถามความสามารถของผู้ช่วยเว็บ และหัวข้อที่ไม่ชัดเจนจะใช้คำตอบ fallback.
ตรวจว่ามีเสียงพูดด้วย VAD ก่อนเรียก Whisper แต่คงเสียงต้นฉบับไว้ทั้งคลิป
เพื่อไม่ตัดคำพูดเบาช่วงต้นหรือท้าย. เสียงที่ไม่พบคำพูดจะตอบ HTTP 422.

`STT_LANGUAGE=thai_first` เป็นค่าเริ่มต้น: ยึดภาษาไทย โดยไม่แปลทั้งประโยค
เป็นอังกฤษ. จะเลือกถอดเป็นอังกฤษทั้งประโยคเมื่อโมเดลตรวจว่าเป็นอังกฤษ
ด้วยความเชื่อมั่นอย่างน้อย 0.90 เท่านั้น; ผลกำกวมหรือภาษาอื่นจะใช้ไทย.
เกณฑ์นี้ช่วยลดการเดาภาษาผิด แต่ยังต้องตรวจคุณภาพกับไมค์และสำเนียงที่ใช้จริง.
`STT_LANGUAGE=th` บังคับไทย, `en` บังคับอังกฤษ และ `auto` เปิดตรวจทุกภาษา
โดยไม่มีเกณฑ์ยึดไทย. AI ยังตอบภาษาไทยตามเดิม.
เวลา AI คิดคำตอบและสร้างเสียงยังขึ้นกับ Ollama และ TTS.

### หน้าจอมือถือและคอมพิวเตอร์

คอมพิวเตอร์และมือถือแนวนอนใช้แชตซ้ายและปุ่มไมค์ขวา. มือถือแนวตั้งจัด
แชตด้านบนและไมค์ด้านล่าง โดยเลื่อนเฉพาะข้อความในแชตและเผื่อขอบจอที่มีรอยบาก.
หน้าเว็บเรียก `/api` และ `/audio` ผ่าน Next.js ไป backend จึงไม่เรียก
`localhost:8000` ของมือถือ. ตั้ง `BACKEND_API_URL` ฝั่งเซิร์ฟเวอร์ Next.js
เมื่อต้องการเปลี่ยนที่อยู่ backend (ค่าเริ่มต้น `http://127.0.0.1:8000`).

เมื่อเปิดจากมือถือให้ใช้ชื่อโฮสต์หรือ IP ของเครื่องที่ให้บริการเว็บ.
การใช้ไมค์บนมือถือจริงต้องเปิดผ่าน HTTPS ที่เบราว์เซอร์เชื่อถือและอนุญาตไมค์;
ข้อยกเว้น localhost ใช้ได้เฉพาะบนอุปกรณ์ที่รันเซิร์ฟเวอร์เอง.

### ทดลอง HTTPS ภายใน Wi-Fi เดียวกัน

เปิด backend และ Next.js ตามปกติ แล้วสร้างใบรับรองสำหรับ IP ของเครื่อง
ที่มือถือจะเชื่อมต่อ โดยรันใน Ubuntu 22.04 จาก root โปรเจกต์:

```bash
python3 scripts/create_dev_https.py --host <LAN_IP_ของคอม>
# หากใช้ development server ให้ระบุ IP นี้ตอนเปิด Next.js ด้วย
cd frontend
DEV_ALLOWED_ORIGINS=<LAN_IP_ของคอม> npm run dev
```

จาก PowerShell ที่ root โปรเจกต์ เปิด proxy ด้วย Node.js บน Windows:

```powershell
node.exe scripts/serve_dev_https.cjs
```

ให้มือถือใช้ Wi-Fi เดียวกับคอม แล้วเปิด `http://<LAN_IP_ของคอม>:3444`
เพื่อดาวน์โหลดใบรับรองสาธารณะ `G1 Thai Local Test CA` และดูขั้นตอนติดตั้ง.
มือถือเป็นผู้ยืนยันการติดตั้งและเชื่อถือใบรับรองเอง สคริปต์ไม่แก้ trust store.
จากนั้นเปิด `https://<LAN_IP_ของคอม>:3443` เพื่อใช้เว็บและขออนุญาตไมค์.
หากยังมีคำเตือนใบรับรอง ให้ตรวจการติดตั้งและชื่อใบรับรองก่อนใช้ไมค์.

CA และใบรับรองทดสอบมีอายุ 7 วัน เก็บที่ `.runtime/https` ซึ่งถูก ignore.
เก็บไฟล์ `.key` ไว้เฉพาะคอมเครื่องทดสอบ; ไฟล์ที่ให้มือถือคือ `.cer` เท่านั้น.
CA ที่เชื่อถือสามารถยืนยันใบรับรองที่ออกโดย CA นี้ได้ จึงควรลบ CA ทดสอบ
ออกจากมือถือเมื่อเลิกทดสอบ. วิธีนี้ใช้ใน LAN โดยไม่มี public tunnel.
หาก IP ของคอมเปลี่ยน ให้สร้างใบรับรองใหม่สำหรับ IP นั้นและรีสตาร์ต proxy.
HTTP พอร์ต 3444 ให้บริการเฉพาะคำแนะนำและ CA สาธารณะ ส่วนเว็บ/API ใช้ HTTPS.

## 4) ตรวจเครือข่าย G1 ก่อนเปิด SDK2

อย่าเดา IP หรือชื่อ network interface. ต่อ PC/adapter และ G1 ตามคู่มือรุ่นของคุณก่อน แล้วหา interface จาก Windows และ WSL:

```powershell
# PowerShell (อ่านอย่างเดียว)
Get-NetAdapter | Format-Table -Auto Name,Status,MacAddress,LinkSpeed
Get-NetIPAddress -AddressFamily IPv4 | Format-Table -Auto InterfaceAlias,IPAddress,PrefixLength
```

```bash
# WSL/Ubuntu (อ่านอย่างเดียว); เปลี่ยนค่า IP เมื่อรู้จาก Unitree แล้ว
bash scripts/check_g1_network.sh
bash scripts/check_g1_network.sh --probe <G1_IP>
```

ต้องเห็นว่า route ไป `<G1_IP>` ออก interface ที่ต่อหุ่นจริง และ ping ผ่านก่อนเท่านั้น. WSL2 ในโหมด NAT ปัจจุบันมักมี `eth0` แบบ virtual (เช่น 172.x.x.x); DDS ของ Unitree ใช้ multicast จึงอาจไม่ผ่าน NAT แม้ ping ผ่าน. หากเป็นเช่นนั้นให้รัน bridge บน Ubuntu native/เครื่อง Linux ที่เสียบ Ethernet กับ G1 โดยตรง หรือกำหนด WSL mirrored networking ตามนโยบาย Windows ของคุณ แล้วทดสอบ SDK2 ใหม่. ยังไม่ควรสั่งเสียงหรือคำสั่งอื่นจนกว่าขั้นตอนนี้ผ่าน.

## 5) ติดตั้ง SDK2 และ build Robot Bridge

ทำบน Linux ที่มี interface ถึง G1 (แนะนำ native Ubuntu 22.04). ตาม README ของ Unitree SDK2 ต้องมี CMake, GCC, Make และ dependencies; SDK2 รองรับทั้ง x86_64/aarch64 และต้องเพิ่ม custom install prefix เข้า `CMAKE_PREFIX_PATH`.

```bash
cd ~
git clone https://github.com/unitreerobotics/unitree_sdk2.git
cmake -S ~/unitree_sdk2 -B ~/unitree_sdk2/build \
  -DBUILD_EXAMPLES=OFF -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$HOME/.local/unitree_sdk2
cmake --build ~/unitree_sdk2/build -j"$(nproc)"
cmake --install ~/unitree_sdk2/build

cd /mnt/d/'Unitree G1 thaiver'/robot_bridge
cmake -S . -B build -DCMAKE_PREFIX_PATH=$HOME/.local/unitree_sdk2
cmake --build build -j"$(nproc)"
```

ยืนยัน interface ที่ต่อหุ่น (`<iface>`) และลอง native TTS เพียงประโยคสั้น ๆ หลังการทดสอบเครือข่ายผ่านแล้ว:

```bash
./robot_bridge/build/g1_audio_bridge --interface <iface> \
  --native-text 'ทดสอบระบบเสียง' --speaker-id 0
```

Unitree SDK2 มี `AudioClient.TtsMaker` แต่ตัวอย่างทางการระบุ speaker 0 เป็นจีนและ 1 เป็นอังกฤษ จึง **ไม่มีหลักฐานว่า native TTS รองรับภาษาไทย**. สำหรับภาษาไทยให้ใช้ Edge TTS สร้าง WAV PCM 16 kHz/mono/16-bit แล้วให้ bridge ส่ง `PlayStream`; SDK2 C++ example ตรวจ format นี้ก่อนเล่นเสียง. โค้ด bridge ทำเช่นเดียวกัน และไม่มี API ด้านการเคลื่อนไหว.

เมื่อลอง native TTS สำเร็จและเสียงออกจากลำโพงแล้วเท่านั้น จึงเปิด bridge จาก backend:

```dotenv
# backend/.env
ROBOT_AUDIO_ENABLED=true
ROBOT_INTERFACE=<iface>
ROBOT_BRIDGE_BIN=/absolute/path/to/robot_bridge/build/g1_audio_bridge
```

รีสตาร์ต FastAPI. เมื่อใช้ `TTS_PROVIDER=edge` ทุกคำตอบจะถูกแปลงเป็น WAV 16 kHz mono แล้ว bridge ส่งเฉพาะ audio stream; หยุดทันทีด้วย Ctrl+C หรือปิด `ROBOT_AUDIO_ENABLED=false` แล้วรีสตาร์ต API. การตั้งค่า `TTS_PROVIDER=unitree` ส่งข้อความไป `TtsMaker` โดยตรง แต่ไม่ควรใช้กับไทยจนกว่าจะพิสูจน์คุณภาพเสียงบนเฟิร์มแวร์ของหุ่นตัวนี้.

## Endpoints

| Method | Path | หน้าที่ |
| --- | --- | --- |
| `GET` | `/health` | สถานะ API และผู้ให้บริการที่ตั้งค่า |
| `POST` | `/api/chat` | รับ `message`, ตอบไทย, สร้างเสียงตาม `speak` |
| `POST` | `/api/transcribe` | รับไฟล์เสียงและถอดเป็นข้อความด้วย Whisper ในเครื่อง |
| `GET` | `/audio/{id}.mp3` | ไฟล์เสียง TTS สำหรับ browser |

ตัวอย่าง request:

```json
{"message":"อธิบายว่า Unitree G1 คืออะไร","speak":true}
```

## ข้อจำกัดที่ตั้งใจไว้

- ไม่มี movement, motor, sport หรือ low-level control ใน repository นี้
- ไม่มีการ hard-code IP ของหุ่น; `ROBOT_INTERFACE` ต้องระบุหลังการตรวจเครือข่าย
- Browser อาจเล่นเสียงได้แม้ยังปิดหุ่นอยู่; การเล่นที่ G1 ต้อง opt-in สองชั้น (`ROBOT_AUDIO_ENABLED=true` และมี bridge binary)
- ไฟล์เสียงสะสมที่ `backend/storage/audio`; ควรตั้งงานลบตาม retention policy ก่อนใช้งานจริง
