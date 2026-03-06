"""Multi-turn conversation manager with LLM-powered response generation."""

import os
import uuid
from typing import Optional

import httpx
from dotenv import load_dotenv

from backend.models import (
    ConversationState,
    ConversationPhase,
    IntentResult,
    ConversationIntent,
    Language,
    Event,
    Booking,
)
from backend.database import search_events, get_event_by_id, get_all_events
from backend.booking import book_event
from backend.recommender import get_alternatives

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")

# In-memory session storage
_sessions: dict[str, ConversationState] = {}


def get_or_create_session(session_id: Optional[str] = None) -> ConversationState:
    """Get an existing session or create a new one."""
    if session_id and session_id in _sessions:
        return _sessions[session_id]

    sid = session_id or str(uuid.uuid4())
    state = ConversationState(session_id=sid)
    _sessions[sid] = state
    return state


def _format_event_short(event: Event, lang: str = "en") -> str:
    """Format event info for voice response."""
    seats = event.available_seats
    if lang == "hi":
        return f"{event.name} — {event.date} को {event.time} बजे, {event.venue} में, {seats} सीटें उपलब्ध"
    elif lang == "te":
        return f"{event.name} — {event.date} న {event.time} కి, {event.venue} లో, {seats} సీట్లు అందుబాటులో"
    else:
        return f"{event.name} — {event.date} at {event.time}, {event.venue}, {seats} seats available"


def _format_booking_confirmation(booking: Booking, event: Event, lang: str = "en") -> str:
    """Format booking confirmation for voice response."""
    if lang == "hi":
        return (
            f"बुकिंग कन्फर्म! {event.name} के लिए {booking.num_tickets} टिकट। "
            f"दिनांक: {event.date}, समय: {event.time}। "
            f"आपका रेफरेंस कोड है: {booking.reference_code}।"
        )
    elif lang == "te":
        return (
            f"బుకింగ్ కన్ఫర్మ్! {event.name} కి {booking.num_tickets} టిక్కెట్లు. "
            f"తేదీ: {event.date}, సమయం: {event.time}. "
            f"మీ రిఫరెన్స్ కోడ్: {booking.reference_code}."
        )
    else:
        return (
            f"Booking confirmed! {booking.num_tickets} ticket(s) for {event.name}. "
            f"Date: {event.date}, Time: {event.time}. "
            f"Your reference code is: {booking.reference_code}."
        )


async def _generate_response_llm(
    user_text: str,
    context: str,
    language: str = "en",
) -> str:
    """Use LLM to generate a natural conversational response."""
    if not OPENROUTER_API_KEY:
        return context  # Fallback to pre-built response

    lang_name = {"en": "English", "hi": "Hindi", "te": "Telugu"}.get(language, "English")

    system_prompt = f"""You are a friendly, conversational event booking assistant.
Respond in {lang_name} language ONLY.
Keep responses short (2-3 sentences max), conversational, and natural — not robotic.
You are speaking to the user via voice, so be warm and helpful.
Use the provided context to formulate your response. Do not make up events or details.
If the context contains event listings, mention them naturally, don't just dump a list."""

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
                        {"role": "user", "content": f"User said: \"{user_text}\"\n\nContext:\n{context}"},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 300,
                },
            )
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"⚠️ LLM response generation failed: {e}")
        return context


async def process_turn(
    session_id: str,
    intent: IntentResult,
) -> tuple[str, ConversationState, Optional[Booking], list[Event]]:
    """
    Process a single conversation turn.

    Returns:
        (response_text, updated_state, booking_or_none, events_list)
    """
    state = get_or_create_session(session_id)
    state.language = intent.language
    lang = intent.language.value

    response_text = ""
    booking_result: Optional[Booking] = None
    events_shown: list[Event] = []

    # Add user message to history
    state.history.append({"role": "user", "text": intent.raw_text})

    # Helper to resolve relative references (first, second, etc.)
    def resolve_index(text: str) -> Optional[int]:
        text_lower = text.lower()
        if any(w in text_lower for w in ["first", "1st", "top", "this", "it", "one", "pehla", "modati"]):
            return 0
        if any(w in text_lower for w in ["second", "2nd", "next", "doosra", "rendu"]):
            return 1
        if any(w in text_lower for w in ["third", "3rd", "last", "teesra", "moodu"]):
            return 2
        return None

    # ═══════════════════════════════════════════════════════════
    # GREETING
    # ═══════════════════════════════════════════════════════════
    if intent.intent == ConversationIntent.GREETING:
        state.phase = ConversationPhase.GREETING
        greetings = {
            "en": "Hello! I'm your event booking assistant. You can ask me about upcoming events, book tickets, or get recommendations. What would you like to do?",
            "hi": "नमस्ते! मैं आपका इवेंट बुकिंग असिस्टेंट हूं। आप मुझसे आगामी इवेंट्स के बारे में पूछ सकते हैं, टिकट बुक कर सकते हैं, या सुझाव ले सकते हैं। आप क्या करना चाहेंगे?",
            "te": "నమస్కారం! నేను మీ ఈవెంట్ బుకింగ్ అసిస్టెంట్‌ని. మీరు రాబోయే ఈవెంట్‌ల గురించి అడగవచ్చు, టిక్కెట్‌లు బుక్ చేయవచ్చు, లేదా సూచనలు పొందవచ్చు. మీరు ఏమి చేయాలనుకుంటున్నారు?",
        }
        response_text = greetings.get(lang, greetings["en"])

    # ═══════════════════════════════════════════════════════════
    # BROWSE — show available events
    # ═══════════════════════════════════════════════════════════
    elif intent.intent == ConversationIntent.BROWSE:
        state.phase = ConversationPhase.BROWSING

        events = search_events(
            name=intent.event_name,
            category=intent.event_type,
            date=intent.date,
            time=intent.time,
        )

        if not events:
            events = get_all_events()

        # Filter to only available events for display
        available_events = [e for e in events if e.available_seats > 0]
        events_shown = available_events[:5]

        if events_shown:
            event_list = "\n".join([_format_event_short(e, lang) for e in events_shown])
            context = f"Here are the available events:\n{event_list}"
            
            # Set alternatives so they are addressable by index ("first one", etc.)
            state.alternatives = [e.id for e in events_shown]
            
            # If search returned exactly one event, set it as current for potential confirmation
            if len(events_shown) == 1:
                state.current_event_id = events_shown[0].id
                context += f"\nNote: I've identified '{events_shown[0].name}' as the primary match. You can ask me to book it."
            else:
                state.current_event_id = events_shown[0].id # Default to first for "book it"
            
            response_text = await _generate_response_llm(intent.raw_text, context, lang)
        else:
            no_events = {
                "en": "I couldn't find any available events matching your criteria. Would you like to see all upcoming events instead?",
                "hi": "मुझे आपके मापदंडों से मिलते-जुलते कोई उपलब्ध इवेंट नहीं मिले। क्या आप सभी आगामी इवेंट देखना चाहेंगे?",
                "te": "మీ ప్రమాణాలకు సరిపోయే ఈవెంట్‌లు కనుగోనలేకపోయాను. మీరు అన్ని రాబోయే ఈవెంట్‌లను చూడాలనుకుంటున్నారా?",
            }
            response_text = no_events.get(lang, no_events["en"])

    # ═══════════════════════════════════════════════════════════
    # BOOK — attempt to book an event
    # ═══════════════════════════════════════════════════════════
    elif intent.intent == ConversationIntent.BOOK:
        state.phase = ConversationPhase.BOOKING

        # Prioritize intent.num_tickets if user mentioned a number, else use state
        num_tickets = intent.num_tickets
        if num_tickets <= 1 and state.pending_num_tickets and state.pending_num_tickets > 1:
            # Check if user actually said "one" or "1"
            if not any(w in intent.raw_text.lower() for w in ["1", "one", "ek", "okati"]):
                num_tickets = state.pending_num_tickets
        
        state.pending_num_tickets = num_tickets

        # Check for relative references first
        ref_idx = resolve_index(intent.event_name or intent.raw_text)
        target_event = None

        if ref_idx is not None:
            if state.alternatives and ref_idx < len(state.alternatives):
                target_event = get_event_by_id(state.alternatives[ref_idx])
            elif ref_idx == 0 and state.current_event_id:
                target_event = get_event_by_id(state.current_event_id)

        if not target_event:
            # Find the event by search
            events = search_events(
                name=intent.event_name,
                category=intent.event_type,
                date=intent.date,
                time=intent.time,
            )

            if not events and intent.event_name:
                events = search_events(name=intent.event_name)
            elif not events and intent.event_type:
                events = search_events(category=intent.event_type)
            
            if events:
                target_event = events[0]

        if not target_event:
            no_match = {
                "en": f"I couldn't find an event matching '{intent.event_name or intent.event_type or 'your request'}'. Would you like to browse all available events?",
                "hi": f"मुझे '{intent.event_name or intent.event_type or 'आपके अनुरोध'}' से मिलता-जुलता कोई इवेंट नहीं मिला। क्या आप सभी उपलब्ध इवेंट ब्राउज़ करना चाहेंगे?",
                "te": f"'{intent.event_name or intent.event_type or 'మీ అభ్యర్థన'}'కి సరిపోయే ఈవెంట్ కనుగొనలేకపోయాను. మీరు అన్ని అందుబాటులో ఉన్న ఈవెంట్‌లను చూడాలనుకుంటున్నారా?",
            }
            response_text = no_match.get(lang, no_match["en"])

        else:
            # target_event is set, now check availability

            if target_event.is_full or target_event.available_seats < num_tickets:
                # ══════════════════════════════════════════════
                # SMART RECOMMENDATIONS — 'No Disappointment' rule
                # ══════════════════════════════════════════════
                state.phase = ConversationPhase.RECOMMENDING
                alternatives = get_alternatives(
                    event_id=target_event.id,
                    event_name=target_event.name,
                    category=target_event.category,
                    date=target_event.date,
                )
                state.alternatives = [a.id for a in alternatives]
                events_shown = alternatives

                if alternatives:
                    alt_list = "\n".join([
                        f"{i+1}. {_format_event_short(a, lang)}"
                        for i, a in enumerate(alternatives)
                    ])
                    context = (
                        f"The event '{target_event.name}' on {target_event.date} is fully booked. "
                        f"But here are great alternatives:\n{alt_list}\n"
                        f"Ask the user which one they'd like to book."
                    )
                    response_text = await _generate_response_llm(intent.raw_text, context, lang)
                else:
                    sorry = {
                        "en": f"Unfortunately '{target_event.name}' is fully booked and I couldn't find similar alternatives. Would you like to browse other events?",
                        "hi": f"दुर्भाग्य से '{target_event.name}' पूरी तरह बुक है और मुझे समान विकल्प नहीं मिले। क्या आप अन्य इवेंट ब्राउज़ करना चाहेंगे?",
                        "te": f"దురదృష్టవశాత్తు '{target_event.name}' పూర్తిగా బుక్ అయిపోయింది మరియు నాకు సమానమైన ప్రత్యామ్నాయాలు కనుగొనలేకపోయాను. మీరు ఇతర ఈవెంట్‌లను బ్రౌజ్ చేయాలనుకుంటున్నారా?",
                    }
                    response_text = sorry.get(lang, sorry["en"])

            else:
                # Seats available — book it!
                state.current_event_id = target_event.id
                state.pending_num_tickets = num_tickets

                success, msg, booking = book_event(target_event.id, num_tickets, lang)

                if success and booking:
                    state.phase = ConversationPhase.DONE
                    booking_result = booking
                    response_text = _format_booking_confirmation(booking, target_event, lang)
                    response_text = await _generate_response_llm(
                        intent.raw_text,
                        f"Booking is confirmed. Details: {response_text}",
                        lang,
                    )
                else:
                    response_text = msg

    # ═══════════════════════════════════════════════════════════
    # CONFIRM — user confirms an alternative booking
    # ═══════════════════════════════════════════════════════════
    elif intent.intent == ConversationIntent.CONFIRM:
        # Resolve index/reference
        ref_idx = resolve_index(intent.raw_text)
        if ref_idx is None:
            ref_idx = 0  # Default to first if they just say "confirm"
        
        # Case 1: Confirming an alternative from recommendations
        if state.phase == ConversationPhase.RECOMMENDING and state.alternatives:

            if ref_idx < len(state.alternatives):
                alt_event_id = state.alternatives[ref_idx]
                alt_event = get_event_by_id(alt_event_id)
                
                # Check for ticket count in raw text or state
                num_tickets = intent.num_tickets
                if num_tickets <= 1 and state.pending_num_tickets and state.pending_num_tickets > 1:
                    if not any(w in intent.raw_text.lower() for w in ["1", "one", "ek", "okati"]):
                        num_tickets = state.pending_num_tickets

                if alt_event:
                    success, msg, booking = book_event(alt_event_id, num_tickets, lang)
                    if success and booking:
                        state.phase = ConversationPhase.DONE
                        booking_result = booking
                        response_text = _format_booking_confirmation(booking, alt_event, lang)
                        response_text = await _generate_response_llm(
                            intent.raw_text,
                            f"The alternative booking is confirmed! Details: {response_text}",
                            lang,
                        )
                    else:
                        response_text = msg
                else:
                    response_text = "Sorry, that alternative is no longer available."
            else:
                response_text = "I didn't catch which option you'd like. Could you say the number?"
        
        # Case 2: Confirming a direct booking for the current event in context
        elif state.current_event_id:
            event = get_event_by_id(state.current_event_id)
            num_tickets = state.pending_num_tickets or 1
            
            if event:
                if event.available_seats >= num_tickets:
                    success, msg, booking = book_event(event.id, num_tickets, lang)
                    if success and booking:
                        state.phase = ConversationPhase.DONE
                        booking_result = booking
                        response_text = _format_booking_confirmation(booking, event, lang)
                        response_text = await _generate_response_llm(
                            intent.raw_text,
                            f"Booking is confirmed. Details: {response_text}",
                            lang,
                        )
                    else:
                        response_text = msg
                else:
                    # Event became full since we last talked about it
                    state.phase = ConversationPhase.RECOMMENDING
                    alternatives = get_alternatives(event_id=event.id)
                    state.alternatives = [a.id for a in alternatives]
                    events_shown = alternatives
                    
                    context = f"Actually, '{event.name}' just filled up. But here are some alternatives:\n"
                    context += "\n".join([f"{i+1}. {_format_event_short(a, lang)}" for i, a in enumerate(alternatives)])
                    response_text = await _generate_response_llm(intent.raw_text, context, lang)
            else:
                response_text = "I lost track of which event we were discussing. Could you say the event name again?"
        
        else:
            unknown = {
                "en": "I'm not sure what you'd like to confirm. Would you like to browse events or book something?",
                "hi": "मुझे समझ नहीं आया कि आप क्या कन्फर्म करना चाहते हैं। क्या आप इवेंट ब्राउज़ करना या कुछ बुक करना चाहेंगे?",
                "te": "మీరు ఏమి నిర్ధారించాలనుకుంటున్నారో నాకు అర్థం కాలేదు. మీరు ఈవెంట్‌లను బ్రౌజ్ చేయాలా లేదా ఏదైనా బుక్ చేయాలనుకుంటున్నారా?",
            }
            response_text = unknown.get(lang, unknown["en"])

    # ═══════════════════════════════════════════════════════════
    # CANCEL
    # ═══════════════════════════════════════════════════════════
    elif intent.intent == ConversationIntent.CANCEL:
        state.phase = ConversationPhase.GREETING
        state.alternatives = []
        state.current_event_id = None
        cancel_msg = {
            "en": "No problem! Is there anything else I can help you with?",
            "hi": "कोई बात नहीं! क्या मैं आपकी और किसी चीज़ में मदद कर सकता हूं?",
            "te": "ఫర్వాలేదు! నేను మీకు ఇంకా ఏదైనా సహాయం చేయగలనా?",
        }
        response_text = cancel_msg.get(lang, cancel_msg["en"])

    # ═══════════════════════════════════════════════════════════
    # UNKNOWN
    # ═══════════════════════════════════════════════════════════
    else:
        unknown = {
            "en": "I'm not sure I understood that. You can ask me to show events, book tickets, or get recommendations. How can I help?",
            "hi": "मुझे यह समझ नहीं आया। आप मुझसे इवेंट दिखाने, टिकट बुक करने, या सुझाव लेने के लिए कह सकते हैं। मैं कैसे मदद कर सकता हूं?",
            "te": "నాకు అర్థం కాలేదు. మీరు నన్ను ఈవెంట్‌లు చూపించమని, టిక్కెట్‌లు బుక్ చేయమని, లేదా సూచనలు ఇవ్వమని అడగవచ్చు. నేను ఎలా సహాయం చేయగలను?",
        }
        response_text = unknown.get(lang, unknown["en"])

    # Add assistant response to history
    state.history.append({"role": "assistant", "text": response_text})

    return response_text, state, booking_result, events_shown
