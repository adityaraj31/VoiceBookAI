"""Booking engine — slot booking, reference generation, and cancellation."""

import random
import string
from datetime import datetime

from backend.database import check_availability, update_booked_seats, save_booking, get_event_by_id
from backend.models import Booking


def _generate_reference_code() -> str:
    """Generate a unique booking reference code like BK-A3X9F2."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"BK-{suffix}"


def book_event(event_id: int, num_tickets: int = 1, language: str = "en") -> tuple[bool, str, Booking | None]:
    """
    Attempt to book tickets for an event.

    Returns:
        (success, message, booking_or_none)
    """
    event = get_event_by_id(event_id)
    if not event:
        return False, "Event not found.", None

    is_available, available = check_availability(event_id, num_tickets)

    if not is_available:
        if available == 0:
            return False, f"Sorry, '{event.name}' is fully booked.", None
        else:
            return False, f"Only {available} seat(s) left for '{event.name}', but you requested {num_tickets}.", None

    # Atomically update seats
    updated = update_booked_seats(event_id, num_tickets)
    if not updated:
        return False, "Booking failed — seats were taken just now. Please try again.", None

    # Create and save booking
    booking = Booking(
        reference_code=_generate_reference_code(),
        event_id=event_id,
        num_tickets=num_tickets,
        user_language=language,
    )
    booking = save_booking(booking)

    return True, f"Booking confirmed! Reference: {booking.reference_code}", booking
