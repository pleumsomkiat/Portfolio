# Unitree G1 / R1 Thai Voice Chatbot

เว็บสนทนาภาษาไทยสำหรับโครงการ Unitree G1 และ R1 ใช้ Next.js, FastAPI, faster-whisper, Ollama และ Edge TTS

## ความสามารถ

- รับคำถามผ่านข้อความหรือไมโครโฟน แสดงข้อความที่ถอดได้และเล่นเสียงตอบภาษาไทย
- โหมด Hybrid ใช้คำตอบที่ยืนยันไว้สำหรับข้อมูลบริษัท/G1/R1 และใช้ AI สำหรับคำถามทั่วไป
- ฐานข้อมูล R1 ครอบคลุม 11 หัวข้อ แยกรายละเอียด R1 AIR, R1 และ R1 EDU พร้อมแหล่งข้อมูลและวันที่ตรวจสอบ
- หน้าเลือกไมค์และแถบระดับเสียงสำหรับตรวจการรับเสียง

## เริ่มใช้งาน

ใช้ Ubuntu 22.04, Python 3.10 และ Node.js 20.9 ขึ้นไป ติดตั้งและตั้งค่าตาม [คู่มือภาษาไทย](README.th.md) โดยสร้างไฟล์ backend/.env และ frontend/.env.local จากไฟล์ตัวอย่างตามต้องการ

เปิด backend จากโฟลเดอร์นี้

```bash
bash scripts/run_backend.sh
```

เปิด frontend ในอีก terminal

```bash
bash scripts/run_frontend.sh
```

เข้า http://localhost:3000 แล้วลองถาม “R1 สูงเท่าไหร่” หรือ “G1 ทำอะไรได้บ้าง”

## สถานะ

เพิ่มข้อมูล R1 วันที่ 17 พฤศจิกายน 2569 ชุดทดสอบ backend 195 รายการผ่าน
การส่งเสียงออกลำโพง G1 และ R1 ยังรอทดสอบกับหุ่นจริง และตั้ง ROBOT_AUDIO_ENABLED=false เป็นค่าเริ่มต้น

อ้างอิงงานใน [Issue #1](https://github.com/pleumsomkiat/Portfolio/issues/1)
