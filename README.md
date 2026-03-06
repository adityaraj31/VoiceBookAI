# 🎤 VoiceBookAI — AI Voice Event Booking System

A voice-first AI assistant that lets users browse, book, and get recommendations for events entirely through speech in **Telugu (తెలుగు)**, **Hindi (हिन्दी)**, or **English**.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Whisper](https://img.shields.io/badge/Whisper-STT-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎙️ Voice Input | Speak in Telugu, Hindi, or English — auto-detected |
| 🧠 Smart Intent | LLM extracts event, date, time, tickets from natural speech |
| 📅 Event Database | 15 seeded events across 8 categories with real-time availability |
| 🎟️ Instant Booking | Book with voice, get a reference code immediately |
| 💡 No Disappointment | When an event is full, 2–3 alternatives are offered instantly |
| 🔊 Voice Response | Responds back in your language via TTS |
| 💬 Multi-turn Chat | Handles follow-up questions and confirmations |

## 🏗️ Architecture

```
Voice Input → Whisper STT → Language Detection
                    ↓
            Intent Extraction (LLM via OpenRouter)
                    ↓
        Conversation Manager → SQLite DB
                    ↓
         Smart Recommendations (if full)
                    ↓
            gTTS Voice Response → Audio Playback
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- [OpenRouter API Key](https://openrouter.ai/) (for LLM intent extraction)
- FFmpeg (required by Whisper for audio processing)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/ai-voice-booking-system.git
cd ai-voice-booking-system

# 2. Create .env file with your API key
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Install dependencies with uv
uv sync

# 4. Run the server
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 5. Open in browser
# Navigate to http://localhost:8000
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | API key from [OpenRouter](https://openrouter.ai/) |
| `LLM_MODEL` | No | LLM model to use (default: `google/gemini-2.0-flash-001`) |
| `WHISPER_MODEL_SIZE` | No | Whisper model size: `tiny`, `base`, `small` (default: `base`) |

## 🎯 Demo Script

### English
1. Click the 🎤 button and say: **"Hello"**
2. Say: **"Show me events this weekend"**
3. Say: **"Book 2 tickets for the photography workshop"**
4. If event is full, assistant offers alternatives — say: **"Yes, book the first one"**

### Hindi (हिन्दी)
1. Say: **"Namaste"**
2. Say: **"Koi event hai Sunday ko?"**
3. Say: **"Dance workshop ke liye do ticket book karo"**
4. If full: **"Haan, pehla wala book karo"**

### Telugu (తెలుగు)
1. Say: **"Namaskaram"**
2. Say: **"Saturday ki emaina events unnaya?"**
3. Say: **"Photography workshop ki rendu tickets kaavali"**
4. If full: **"Avunu, first option book cheyyi"**

### Using Text Mode
Switch to ⌨️ Text mode for testing without a microphone. Select your language from the dropdown and type your query.

## 📁 Project Structure

```
├── backend/
│   ├── main.py           # FastAPI app + endpoints
│   ├── models.py         # Pydantic data models
│   ├── database.py       # SQLite setup + 15 seeded events
│   ├── booking.py        # Booking engine + reference codes
│   ├── recommender.py    # Smart alternative recommendations
│   ├── stt.py            # Whisper speech-to-text
│   ├── tts.py            # gTTS text-to-speech
│   ├── intent.py         # LLM intent extraction
│   └── conversation.py   # Multi-turn conversation manager
├── frontend/
│   ├── index.html        # Main UI
│   ├── style.css         # Dark glassmorphic theme
│   └── app.js            # Voice recording + API integration
├── tests/
│   ├── test_database.py
│   ├── test_booking.py
│   └── test_recommender.py
├── pyproject.toml
├── .env.example
└── README.md
```

## 🧪 Running Tests

```bash
uv run pytest tests/ -v
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python + FastAPI |
| STT | OpenAI Whisper (local) |
| TTS | gTTS (Google TTS) |
| LLM | Gemini via OpenRouter |
| Database | SQLite |
| Frontend | HTML + CSS + JavaScript |
| Package Manager | uv |

## 📜 License

MIT
