"""LLM-based intent extraction using OpenRouter API."""

import json
import os
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

from backend.models import IntentResult, ConversationIntent, Language

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")

# Current date for resolving relative dates
TODAY = datetime.now()

SYSTEM_PROMPT = """You are an intent extraction engine for an event booking system.
You support three languages: English, Hindi, and Telugu.

Given a user's voice transcription, extract the following fields as JSON:
{{
    "intent": "browse" | "book" | "confirm" | "cancel" | "recommend" | "greeting" | "unknown",
    "event_name": "string or null — the event name or keyword the user mentioned",
    "event_type": "string or null — category like Music, Dance, Photography, Comedy, Art, Tech, Cooking, Yoga",
    "date": "YYYY-MM-DD or null — resolve relative dates like 'tomorrow', 'this Saturday', 'Sunday' relative to today: {today}",
    "time": "HH:MM or null — in 24h format",
    "num_tickets": integer (default 1),
    "language": "en" | "hi" | "te" — the language the user spoke in
}}

Rules:
- "tomorrow" = {tomorrow}
- "this Saturday" or "Saturday" = {saturday}
- "this Sunday" or "Sunday" = {sunday}
- If the user asks about events, lists, or what's available → intent = "browse"
- If the user wants to book/reserve tickets → intent = "book"
- If the user says "yes", "haan", "avunu", "book it", etc. after being offered alternatives → intent = "confirm"
- If the user says "no", "nahi", "vaddu", "cancel" → intent = "cancel"
- If the user just says hello/hi/namaste → intent = "greeting"
- Extract num_tickets from phrases like "2 tickets", "do tickets", "rendu tickets"
- Always respond with valid JSON only — no explanation text.
"""


def _get_system_prompt() -> str:
    """Build system prompt with resolved dates."""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    # Find next Saturday and Sunday
    days_until_sat = (5 - today.weekday()) % 7
    if days_until_sat == 0:
        days_until_sat = 7
    saturday = today + timedelta(days=days_until_sat)

    days_until_sun = (6 - today.weekday()) % 7
    if days_until_sun == 0:
        days_until_sun = 7
    sunday = today + timedelta(days=days_until_sun)

    return SYSTEM_PROMPT.format(
        today=today.strftime("%Y-%m-%d"),
        tomorrow=tomorrow.strftime("%Y-%m-%d"),
        saturday=saturday.strftime("%Y-%m-%d"),
        sunday=sunday.strftime("%Y-%m-%d"),
    )


async def extract_intent(text: str, detected_language: str = "en") -> IntentResult:
    """
    Extract intent and entities from a user's transcribed text using an LLM.

    Args:
        text: The transcribed user input
        detected_language: Language detected by STT ('en', 'hi', 'te')

    Returns:
        IntentResult with extracted fields
    """
    if not OPENROUTER_API_KEY:
        # Fallback: basic keyword-based intent detection
        return _fallback_intent(text, detected_language)

    system_prompt = _get_system_prompt()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"User said: \"{text}\""},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Parse JSON from LLM response
        parsed = json.loads(content)

        return IntentResult(
            intent=ConversationIntent(parsed.get("intent", "unknown")),
            event_name=parsed.get("event_name"),
            event_type=parsed.get("event_type"),
            date=parsed.get("date"),
            time=parsed.get("time"),
            num_tickets=parsed.get("num_tickets", 1),
            language=Language(parsed.get("language", detected_language)),
            raw_text=text,
            confidence=0.9,
        )

    except Exception as e:
        print(f"⚠️ LLM intent extraction failed: {e}")
        return _fallback_intent(text, detected_language)


def _fallback_intent(text: str, detected_language: str = "en") -> IntentResult:
    """Simple keyword-based fallback when LLM is not available."""
    text_lower = text.lower()

    intent = ConversationIntent.UNKNOWN

    # Greeting detection
    greetings = ["hello", "hi", "hey", "namaste", "namaskar", "namasthe", "vanakkam"]
    if any(g in text_lower for g in greetings):
        intent = ConversationIntent.GREETING

    # Browse detection
    browse_kw = ["show", "list", "what", "events", "available", "kya", "koi", "emi", "entha", "chupinchu"]
    if any(k in text_lower for k in browse_kw):
        intent = ConversationIntent.BROWSE

    # Book detection
    book_kw = ["book", "reserve", "ticket", "register", "seats", "kaavali", "chahiye", "booking"]
    if any(k in text_lower for k in book_kw):
        intent = ConversationIntent.BOOK

    # Confirm detection
    confirm_kw = ["yes", "haan", "han", "avunu", "ok", "sure", "book it", "confirm"]
    if any(k in text_lower for k in confirm_kw):
        intent = ConversationIntent.CONFIRM

    # Cancel detection
    cancel_kw = ["no", "nahi", "vaddu", "cancel", "stop", "nope"]
    if any(k in text_lower for k in cancel_kw):
        intent = ConversationIntent.CANCEL

    return IntentResult(
        intent=intent,
        language=Language(detected_language) if detected_language in ("en", "hi", "te") else Language.ENGLISH,
        raw_text=text,
        confidence=0.5,
    )
