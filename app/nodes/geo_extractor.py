from pathlib import Path

from app.llm import extraction_llm, structured_llm
from app.models.event import _GeoExtraction
from app.state import EventState


PROMPT = Path("app/prompts/geo_extractor.txt").read_text(encoding="utf-8")

structured_geo = structured_llm(extraction_llm, _GeoExtraction)


def geo_extractor(state: EventState) -> dict:
    print("\n========== GEO EXTRACTOR ==========")

    if not state["is_event"]:
        print("No event found. Skipping extraction.")
        return {"geo": None}

    raw = structured_geo.invoke(
        f"""{PROMPT}

Articolo:

{state["article"]}
"""
    )

    print("Extracted Geo:")
    print(raw)

    return {"geo": raw}
