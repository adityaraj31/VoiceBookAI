"""Smart recommendation engine — the 'No Disappointment' rule.

When an event is fully booked, this module finds the best alternatives:
1. Same event on a different date
2. Same category on the same day
3. Nearby time slots with availability
"""

from backend.database import get_all_events, get_event_by_id
from backend.models import Event


def get_alternatives(
    event_id: int | None = None,
    event_name: str | None = None,
    category: str | None = None,
    date: str | None = None,
    max_results: int = 3,
) -> list[Event]:
    """
    Find alternative events when the requested one is full.

    Priority:
    1. Same event name on a different date
    2. Same category on the same date
    3. Same category on nearby dates
    """
    all_events = get_all_events()
    original = get_event_by_id(event_id) if event_id else None

    if original:
        event_name = event_name or original.name
        category = category or original.category
        date = date or original.date

    alternatives: list[Event] = []
    seen_ids: set[int] = set()
    if event_id:
        seen_ids.add(event_id)

    # Priority 1: Same event name, different date (with availability)
    if event_name:
        name_lower = event_name.lower()
        for ev in all_events:
            if ev.id in seen_ids:
                continue
            if name_lower in ev.name.lower() and ev.available_seats > 0:
                if not date or ev.date != date:
                    alternatives.append(ev)
                    seen_ids.add(ev.id)

    # Priority 2: Same category, same date (with availability)
    if category and date:
        cat_lower = category.lower()
        for ev in all_events:
            if ev.id in seen_ids:
                continue
            if cat_lower in ev.category.lower() and ev.date == date and ev.available_seats > 0:
                alternatives.append(ev)
                seen_ids.add(ev.id)

    # Priority 3: Same category, any date (with availability)
    if category and len(alternatives) < max_results:
        cat_lower = category.lower()
        for ev in all_events:
            if ev.id in seen_ids:
                continue
            if cat_lower in ev.category.lower() and ev.available_seats > 0:
                alternatives.append(ev)
                seen_ids.add(ev.id)

    # Priority 4: Any event with availability on the same date
    if date and len(alternatives) < max_results:
        for ev in all_events:
            if ev.id in seen_ids:
                continue
            if ev.date == date and ev.available_seats > 0:
                alternatives.append(ev)
                seen_ids.add(ev.id)

    return alternatives[:max_results]
