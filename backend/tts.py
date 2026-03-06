"""Text-to-Speech using gTTS (Google Text-to-Speech)."""

import io
import tempfile
from pathlib import Path

from gtts import gTTS


# Language code mapping for gTTS
LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "te": "te",
}


def synthesize(text: str, language: str = "en") -> bytes:
    """
    Convert text to speech audio (MP3 bytes).

    Args:
        text: The text to speak
        language: Language code ('en', 'hi', 'te')

    Returns:
        MP3 audio bytes
    """
    lang_code = LANG_MAP.get(language, "en")

    tts = gTTS(text=text, lang=lang_code, slow=False)

    # Write to in-memory buffer
    mp3_buffer = io.BytesIO()
    tts.write_to_fp(mp3_buffer)
    mp3_buffer.seek(0)

    return mp3_buffer.read()


def synthesize_to_file(text: str, language: str = "en", output_path: str | None = None) -> str:
    """
    Convert text to speech and save as MP3 file.

    Args:
        text: The text to speak
        language: Language code ('en', 'hi', 'te')
        output_path: Optional path to save. If None, creates a temp file.

    Returns:
        Path to the saved MP3 file
    """
    audio_bytes = synthesize(text, language)

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = tmp.name
        tmp.close()

    Path(output_path).write_bytes(audio_bytes)
    return output_path
