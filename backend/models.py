"""Pydantic models for the AI Voice Booking System."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TELUGU = "te"


class ConversationIntent(str, Enum):
    BROWSE = "browse"
    BOOK = "book"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    RECOMMEND = "recommend"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class ConversationPhase(str, Enum):
    GREETING = "greeting"
    BROWSING = "browsing"
    BOOKING = "booking"
    RECOMMENDING = "recommending"
    CONFIRMING = "confirming"
    DONE = "done"


class Event(BaseModel):
    id: int
    name: str
    category: str
    date: str
    time: str
    venue: str
    total_seats: int
    booked_seats: int
    description: str
    description_hi: str = ""
    description_te: str = ""

    @property
    def available_seats(self) -> int:
        return self.total_seats - self.booked_seats

    @property
    def is_full(self) -> bool:
        return self.available_seats <= 0


class Booking(BaseModel):
    id: Optional[int] = None
    reference_code: str
    event_id: int
    num_tickets: int
    user_language: str = "en"
    booked_at: Optional[str] = None
    event_name: Optional[str] = None # Added for UI convenience


class IntentResult(BaseModel):
    intent: ConversationIntent = ConversationIntent.UNKNOWN
    event_name: Optional[str] = None
    event_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    num_tickets: int = 1
    language: Language = Language.ENGLISH
    raw_text: str = ""
    confidence: float = 0.0


class ConversationState(BaseModel):
    session_id: str
    phase: ConversationPhase = ConversationPhase.GREETING
    language: Language = Language.ENGLISH
    current_event_id: Optional[int] = None
    pending_num_tickets: int = 1
    alternatives: list[int] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)


class VoiceResponse(BaseModel):
    transcript: str = ""
    detected_language: str = "en"
    intent: str = ""
    response_text: str = ""
    booking: Optional[Booking] = None
    events: list[Event] = Field(default_factory=list)
    audio_url: Optional[str] = None
