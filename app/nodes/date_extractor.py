from pathlib import Path

from app.llm import extraction_llm
from app.models.event import _DateExtraction
from app.state import EventState


PROMPT = Path("app/prompts/date_extractor.txt").read_text(encoding="utf-8")

structured_llm = extraction_llm.with_structured_output(_DateExtraction)


def date_extractor(state: EventState) -> dict:
    print("\n========== DATE EXTRACTOR ==========")

    if not state["is_event"]:
        print("No event found. Skipping extraction.")
        return {"event": None}

    raw = structured_llm.invoke(
        f"""{PROMPT}

Data di pubblicazione: {state["publication_date"]}

Articolo:

{state["article"]}
"""
    )

    print("Extracted Dates:")
    print(raw)

    geo = state.get("geo")
    if geo is None:
        return {"event": None}

    from app.models.event import Event, EventDate

    def _normalize_end_date(end_date):
        if end_date is not None and all(
            getattr(end_date, f) is None for f in ("day", "month", "year")
        ):
            return None
        return end_date

    event = Event(
        category=geo.category,
        place=geo.place,
        county=geo.county,
        street=geo.street,
        description=geo.description,
        start_date=raw.start_date,
        end_date=_normalize_end_date(raw.end_date),
    )

    print("Merged Event:")
    print(event)

    return {"event": event}
