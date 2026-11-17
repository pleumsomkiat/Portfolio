from __future__ import annotations

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .models import ChatRequest, ChatResponse, HealthResponse
from .knowledge import build_knowledge_context
from .services.ai import generate_reply
from .services.robot_audio import deliver_to_robot
from .services.tts import synthesize_thai
from .services.stt import get_model, transcribe_audio, warm_up_model
from .settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load once at startup so the first question does not pay the model load time.
    model = await run_in_threadpool(get_model)
    if model is not None:
        await run_in_threadpool(warm_up_model, model)
    yield


app = FastAPI(title="Unitree G1 Thai Chatbot API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.mount("/audio", StaticFiles(directory=str(settings.audio_dir)), name="audio")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        ai_provider=settings.ai_provider,
        tts_provider=settings.tts_provider,
        robot_audio_enabled=settings.robot_audio_enabled,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        # Prepared routing happens before general AI in hybrid mode. Neither
        # keyword nor hybrid routing needs broad document retrieval here.
        knowledge_context = (
            "" if settings.ai_provider.lower().strip() in {"keywords", "hybrid"}
            else build_knowledge_context(request.message)
        )

        # เลือกคำตอบตามโหมดที่ตั้งค่าไว้
        answer = await generate_reply(
            message=request.message,
            settings=settings,
            knowledge_context=knowledge_context,
        )

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # หากผู้ใช้ไม่ต้องการเสียง
    if not request.speak:
        return ChatResponse(
            answer=answer,
            audio_status="ผู้ใช้ปิดการสร้างเสียง",
            robot_status="ไม่ส่งไปหุ่นยนต์เมื่อไม่ได้สร้างเสียง",
        )

    # สร้างเสียงภาษาไทย
    tts = await synthesize_thai(answer, settings)

    audio_url = (
        f"/audio/{Path(tts.mp3_path).name}"
        if tts.mp3_path
        else None
    )

    # ส่งเสียงไปยังลำโพงหุ่นยนต์ (เมื่อเปิดใช้งานเท่านั้น)
    robot_status = await deliver_to_robot(
        text=answer,
        mp3_path=tts.mp3_path,
        settings=settings,
    )

    return ChatResponse(
        answer=answer,
        audio_url=audio_url,
        audio_status=tts.status,
        robot_status=robot_status,
    )

@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    suffix = Path(file.filename or "voice.webm").suffix.lower()

    if suffix not in (".webm", ".mp4", ".ogg", ".wav"):
        raise HTTPException(
            status_code=400,
            detail="ไม่รองรับไฟล์เสียงประเภทนี้",
        )

    audio_bytes = await file.read(15 * 1024 * 1024 + 1)

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="ไม่ได้รับข้อมูลเสียง",
        )

    if len(audio_bytes) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="ไฟล์เสียงมีขนาดใหญ่เกินไป",
        )

    try:
        text = await run_in_threadpool(
            transcribe_audio,
            audio_bytes,
            suffix,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Whisper ทำงานไม่สำเร็จ: {exc}",
        ) from exc

    if not text:
        raise HTTPException(
            status_code=422,
            detail="ไม่พบคำพูดในไฟล์เสียง",
        )

    return {"text": text}
