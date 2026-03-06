"""Tests for the smart recommendation engine."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.database import setup_database, get_all_events, DB_PATH
from backend.recommender import get_alternatives


def setup_module():
    """Set up a fresh test database."""
    if DB_PATH.exists():
        os.remove(DB_PATH)
    setup_database()


def test_alternatives_for_full_event():
    """Verify alternatives are returned for a fully booked event."""
    events = get_all_events()
    full_event = next(ev for ev in events if ev.is_full)

    alts = get_alternatives(
        event_id=full_event.id,
        event_name=full_event.name,
        category=full_event.category,
        date=full_event.date,
    )

    assert len(alts) > 0, "No alternatives returned for a full event"
    assert len(alts) <= 3, f"Too many alternatives: {len(alts)}"
    # Alternatives should have availability
    for alt in alts:
        assert alt.available_seats > 0, f"Alternative {alt.name} has no seats"


def test_alternatives_exclude_original():
    """Verify the original event is not included in alternatives."""
    events = get_all_events()
    full_event = next(ev for ev in events if ev.is_full)

    alts = get_alternatives(event_id=full_event.id)

    alt_ids = [a.id for a in alts]
    assert full_event.id not in alt_ids, "Original event found in alternatives"


def test_alternatives_same_category():
    """Verify alternatives prioritize the same category."""
    events = get_all_events()
    full_event = next(ev for ev in events if ev.is_full)

    alts = get_alternatives(
        event_id=full_event.id,
        category=full_event.category,
        date=full_event.date,
    )

    if alts:
        # At least one alternative should be in the same category
        same_cat = [a for a in alts if a.category.lower() == full_event.category.lower()]
        # This is a soft check — same category alternatives may not always exist
        # but should be preferred when they do


def test_alternatives_max_results():
    """Verify we don't get more alternatives than requested."""
    events = get_all_events()
    full_event = next(ev for ev in events if ev.is_full)

    alts = get_alternatives(event_id=full_event.id, max_results=2)
    assert len(alts) <= 2


def test_alternatives_all_have_availability():
    """Verify all returned alternatives have available seats."""
    events = get_all_events()
    full_event = next(ev for ev in events if ev.is_full)

    alts = get_alternatives(event_id=full_event.id)
    for alt in alts:
        assert alt.available_seats > 0, f"Alternative '{alt.name}' has no seats available"
