"""Tests for the database module."""

import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.database import (
    init_db,
    seed_events,
    get_all_events,
    get_event_by_id,
    search_events,
    check_availability,
    setup_database,
    DB_PATH,
)


def setup_module():
    """Set up a fresh test database."""
    # Use a test database
    if DB_PATH.exists():
        os.remove(DB_PATH)
    setup_database()


def test_seed_events_count():
    """Verify that exactly 15 events are seeded."""
    events = get_all_events()
    assert len(events) == 15, f"Expected 15 events, got {len(events)}"


def test_event_has_required_fields():
    """Verify each event has all required fields."""
    events = get_all_events()
    for ev in events:
        assert ev.name, f"Event {ev.id} missing name"
        assert ev.category, f"Event {ev.id} missing category"
        assert ev.date, f"Event {ev.id} missing date"
        assert ev.time, f"Event {ev.id} missing time"
        assert ev.venue, f"Event {ev.id} missing venue"
        assert ev.total_seats > 0, f"Event {ev.id} has no seats"


def test_event_categories():
    """Verify events span multiple categories."""
    events = get_all_events()
    categories = set(ev.category for ev in events)
    assert len(categories) >= 5, f"Expected at least 5 categories, got {categories}"


def test_some_events_fully_booked():
    """Verify that some events are fully booked (for testing recommendations)."""
    events = get_all_events()
    full_events = [ev for ev in events if ev.is_full]
    assert len(full_events) >= 2, f"Expected at least 2 fully booked events, got {len(full_events)}"


def test_get_event_by_id():
    """Verify fetching a specific event works."""
    event = get_event_by_id(1)
    assert event is not None
    assert event.id == 1


def test_get_event_by_invalid_id():
    """Verify fetching a non-existent event returns None."""
    event = get_event_by_id(999)
    assert event is None


def test_search_by_category():
    """Verify searching by category works."""
    music_events = search_events(category="Music")
    assert len(music_events) > 0
    for ev in music_events:
        assert "music" in ev.category.lower()


def test_search_by_name():
    """Verify searching by name with partial match works."""
    events = search_events(name="yoga")
    assert len(events) > 0
    for ev in events:
        assert "yoga" in ev.name.lower()


def test_check_availability_available():
    """Verify availability check for an event with seats."""
    # Find an event with available seats
    events = get_all_events()
    available_event = next(ev for ev in events if ev.available_seats > 0)
    is_avail, avail_count = check_availability(available_event.id, 1)
    assert is_avail is True
    assert avail_count > 0


def test_check_availability_full():
    """Verify availability check for a fully booked event."""
    events = get_all_events()
    full_event = next(ev for ev in events if ev.is_full)
    is_avail, avail_count = check_availability(full_event.id, 1)
    assert is_avail is False
    assert avail_count == 0


def test_multilingual_descriptions():
    """Verify events have Hindi and Telugu descriptions."""
    events = get_all_events()
    for ev in events:
        assert ev.description_hi, f"Event '{ev.name}' missing Hindi description"
        assert ev.description_te, f"Event '{ev.name}' missing Telugu description"
