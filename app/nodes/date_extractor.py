from pathlib import Path

from app.llm import extraction_llm, structured_llm
from app.models.event import _DateExtraction, EventDate
from app.state import EventState


PROMPT = Path("app/prompts/date_extractor.txt").read_text(encoding="utf-8")

structured_date = structured_llm(extraction_llm, _DateExtraction)


def _validate_date(date: EventDate | None, label: str) -> EventDate | None:
    if date is None:
        return None
    if date.day is not None and not (1 <= date.day <= 31):
        print(f"  {label}.day={date.day} invalid. Set to None.")
        date.day = None
    if date.month is not None and not (1 <= date.month <= 12):
        print(f"  {label}.month={date.month} invalid. Set to None.")
        date.month = None
    if date.year is not None and not (2000 <= date.year <= 2100):
        print(f"  {label}.year={date.year} invalid. Set to None.")
        date.year = None
    if all(v is None for v in (date.day, date.month, date.year)):
        return None
    return date


def _normalize_end_date(end_date: EventDate | None) -> EventDate | None:
    if end_date is not None and all(
        getattr(end_date, f) is None for f in ("day", "month", "year")
    ):
        return None
    return end_date


def date_extractor(state: EventState) -> dict:
    print("\n========== DATE EXTRACTOR ==========")

    if not state["is_event"]:
        print("No event found. Skipping extraction.")
        return {"event": None}

    raw = structured_date.invoke(
        f"""{PROMPT}

Data di pubblicazione: {state["publication_date"]}

Articolo:

{state["article"]}
"""
    )

    print("Extracted Dates:")
    print(raw)

    start_date = _validate_date(raw.start_date, "start_date")
    end_date = _validate_date(raw.end_date, "end_date")
    end_date = _normalize_end_date(end_date)

    geo = state.get("geo")
    if geo is None:
        return {"event": None}

    from app.models.event import Event

    event = Event(
        category=geo.category,
        place=geo.place,
        county=geo.county,
        street=geo.street,
        description=geo.description,
        start_date=start_date or EventDate(),
        end_date=end_date,
    )

    print("Merged Event:")
    print(event)

    return {"event": event}
