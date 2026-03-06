"""Tests for the booking engine."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.database import setup_database, get_all_events, get_event_by_id, DB_PATH
from backend.booking import book_event, _generate_reference_code


def setup_module():
    """Set up a fresh test database."""
    if DB_PATH.exists():
        os.remove(DB_PATH)
    setup_database()


def test_reference_code_format():
    """Verify reference codes follow BK-XXXXXX format."""
    code = _generate_reference_code()
    assert code.startswith("BK-"), f"Code {code} doesn't start with BK-"
    assert len(code) == 9, f"Code {code} length is {len(code)}, expected 9"


def test_reference_code_uniqueness():
    """Verify reference codes are unique."""
    codes = set(_generate_reference_code() for _ in range(100))
    assert len(codes) == 100, "Reference codes are not unique"


def test_book_available_event():
    """Verify booking an available event succeeds."""
    events = get_all_events()
    available_event = next(ev for ev in events if ev.available_seats > 0)
    original_booked = available_event.booked_seats

    success, msg, booking = book_event(available_event.id, 1)

    assert success is True, f"Booking failed: {msg}"
    assert booking is not None
    assert booking.reference_code.startswith("BK-")
    assert booking.event_id == available_event.id
    assert booking.num_tickets == 1

    # Verify seat count updated
    updated = get_event_by_id(available_event.id)
    assert updated.booked_seats == original_booked + 1


def test_book_full_event():
    """Verify booking a fully booked event fails."""
    events = get_all_events()
    full_event = next(ev for ev in events if ev.is_full)

    success, msg, booking = book_event(full_event.id, 1)

    assert success is False
    assert booking is None
    assert "fully booked" in msg.lower() or "full" in msg.lower()


def test_book_nonexistent_event():
    """Verify booking a non-existent event fails."""
    success, msg, booking = book_event(999, 1)
    assert success is False
    assert booking is None
    assert "not found" in msg.lower()


def test_book_too_many_tickets():
    """Verify booking more tickets than available fails."""
    events = get_all_events()
    # Find an event with some but limited availability
    limited_event = next(
        (ev for ev in events if 0 < ev.available_seats < 10),
        None
    )
    if limited_event is None:
        return  # Skip if no such event

    too_many = limited_event.available_seats + 5
    success, msg, booking = book_event(limited_event.id, too_many)

    assert success is False
    assert booking is None
