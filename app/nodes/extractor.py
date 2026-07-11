from pathlib import Path

from app.llm import extraction_llm
from app.models.event import Event, _EventExtraction
from app.state import EventState


PROMPT = Path("app/prompts/extractor.txt").read_text(encoding="utf-8")

structured_llm = extraction_llm.with_structured_output(_EventExtraction)


def _to_event(raw: _EventExtraction) -> Event:
    return Event(
        category=raw.category,
        city=raw.city,
        location=raw.location or None,
        start_date=raw.start_date,
        end_date=raw.end_date,
    )


def _normalize_event(event: Event) -> Event:
    if event.end_date is not None and all(
        getattr(event.end_date, f) is None for f in ("day", "month", "year")
    ):
        event.end_date = None
    return event


def event_extractor(state: EventState) -> dict:
    print("\n========== EVENT EXTRACTOR ==========")

    if not state["is_event"]:
        print("No event found. Skipping extraction.")

        return {
            "event": None,
        }

    raw = structured_llm.invoke(
        f"""{PROMPT}

Data di pubblicazione: {state["publication_date"]}

Articolo:

{state["article"]}
"""
    )

    event = _to_event(raw)
    event = _normalize_event(event)

    print("Extracted Event:")
    print(event)

    return {
        "event": event,
    }
