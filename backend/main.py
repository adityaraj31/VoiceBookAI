"""FastAPI backend — main application entry point."""

import os
import uuid
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.database import setup_database, get_all_events, get_event_by_id, get_all_bookings
from backend.stt import transcribe_upload
from backend.tts import synthesize
from backend.intent import extract_intent
from backend.conversation import process_turn, get_or_create_session
from backend.models import VoiceResponse, Event

# ── App Setup ────────────────────────────────────────────────

app = FastAPI(
    title="AI Voice Booking System",
    description="Voice-first multilingual event booking assistant",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory for audio files
AUDIO_DIR = Path(tempfile.gettempdir()) / "voice_booking_audio"
AUDIO_DIR.mkdir(exist_ok=True)

# Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Startup ──────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    setup_database()
    print("🚀 AI Voice Booking System is ready!")


# ── Voice Interaction Endpoint ───────────────────────────────

@app.post("/api/voice")
async def voice_interaction(
    audio: UploadFile = File(...),
    session_id: str = Form(default=""),
):
    """
    Main voice interaction endpoint.
    Accepts audio upload, processes through STT → Intent → Conversation → TTS pipeline.
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    # Step 1: Speech-to-Text
    audio_bytes = await audio.read()
    stt_result = await transcribe_upload(audio_bytes, audio.filename or "audio.webm")

    transcript = stt_result["text"]
    detected_lang = stt_result["language"]

    if not transcript.strip():
        return VoiceResponse(
            transcript="",
            detected_language=detected_lang,
            intent="unknown",
            response_text="I didn't catch that. Could you please speak again?",
        )

    # Step 2: Intent Extraction
    intent = await extract_intent(transcript, detected_lang)

    # Step 3: Conversation Processing
    response_text, state, booking, events = await process_turn(session_id, intent)

    # Step 4: Text-to-Speech
    audio_filename = f"{session_id}_{uuid.uuid4().hex[:8]}.mp3"
    audio_path = AUDIO_DIR / audio_filename

    try:
        tts_bytes = synthesize(response_text, detected_lang)
        audio_path.write_bytes(tts_bytes)
        audio_url = f"/api/audio/{audio_filename}"
    except Exception as e:
        print(f"⚠️ TTS failed: {e}")
        audio_url = None

    return {
        "session_id": session_id,
        "transcript": transcript,
        "detected_language": detected_lang,
        "intent": intent.intent.value,
        "response_text": response_text,
        "booking": booking.model_dump() if booking else None,
        "events": [e.model_dump() for e in events],
        "audio_url": audio_url,
    }


# ── Text Interaction Endpoint (for testing) ──────────────────

@app.post("/api/text")
async def text_interaction(
    text: str = Form(...),
    language: str = Form(default="en"),
    session_id: str = Form(default=""),
):
    """
    Text-based interaction endpoint for testing without microphone.
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    # Intent Extraction
    intent = await extract_intent(text, language)

    # Conversation Processing
    response_text, state, booking, events = await process_turn(session_id, intent)

    # TTS
    audio_filename = f"{session_id}_{uuid.uuid4().hex[:8]}.mp3"
    audio_path = AUDIO_DIR / audio_filename

    try:
        tts_bytes = synthesize(response_text, language)
        audio_path.write_bytes(tts_bytes)
        audio_url = f"/api/audio/{audio_filename}"
    except Exception as e:
        print(f"⚠️ TTS failed: {e}")
        audio_url = None

    return {
        "session_id": session_id,
        "transcript": text,
        "detected_language": language,
        "intent": intent.intent.value,
        "response_text": response_text,
        "booking": booking.model_dump() if booking else None,
        "events": [e.model_dump() for e in events],
        "audio_url": audio_url,
    }


# ── Audio Serving ────────────────────────────────────────────

@app.get("/api/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated TTS audio files."""
    file_path = AUDIO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(file_path), media_type="audio/mpeg")


# ── Event & Booking API ─────────────────────────────────────

@app.get("/api/events")
async def list_events():
    """List all events."""
    events = get_all_events()
    return {"events": [e.model_dump() for e in events]}


@app.get("/api/events/{event_id}")
async def get_event(event_id: int):
    """Get a single event."""
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.model_dump()


@app.get("/api/bookings")
async def list_bookings_api():
    """List all bookings."""
    bookings = get_all_bookings()
    return {"bookings": bookings}


# ── Serve Frontend ───────────────────────────────────────────

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
