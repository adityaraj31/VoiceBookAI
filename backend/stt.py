"""Speech-to-Text using OpenAI Whisper (local model)."""

import os
import tempfile
from pathlib import Path

# Ensure bundled FFmpeg is available before importing whisper
import static_ffmpeg
static_ffmpeg.add_paths()

import whisper

# Load model once at module level (lazy init)
_model = None


def _get_model():
    """Lazy-load the Whisper model."""
    global _model
    if _model is None:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        print(f"🎙️ Loading Whisper model: {model_size}")
        _model = whisper.load_model(model_size)
        print("✅ Whisper model loaded.")
    return _model


def transcribe(audio_path: str) -> dict:
    """
    Transcribe an audio file and auto-detect language.

    Args:
        audio_path: Path to the audio file (WAV, MP3, WebM, etc.)

    Returns:
        {
            "text": "transcribed text",
            "language": "en" | "hi" | "te",
            "language_name": "English" | "Hindi" | "Telugu"
        }
    """
    model = _get_model()

    # Transcribe with language detection
    result = model.transcribe(
        audio_path,
        task="transcribe",
        fp16=False,  # Use fp32 for CPU compatibility
    )

    detected_lang = result.get("language", "en")
    text = result.get("text", "").strip()

    # Map language codes to names
    lang_names = {
        "en": "English",
        "hi": "Hindi",
        "te": "Telugu",
    }

    # Normalize language — if not one of our supported languages, default to English
    if detected_lang not in ("en", "hi", "te"):
        detected_lang = "en"

    return {
        "text": text,
        "language": detected_lang,
        "language_name": lang_names.get(detected_lang, "English"),
    }


async def transcribe_upload(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    Transcribe from uploaded audio bytes.
    Saves to a temp file, transcribes, then cleans up.
    """
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        return transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)
