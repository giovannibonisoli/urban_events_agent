import csv
import json
from pathlib import Path
from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)

from app.llm import extraction_llm, structured_llm
from app.models.geo import EventGeoExtraction
from app.state import NewsArticleState

SYSTEM_PROMPT = Path("app/prompts/geo_extractor.txt").read_text(encoding="utf-8")

try:
    with open("app/prompts/examples/geo_extractor_examples.json", encoding="utf-8") as f:
        raw_examples = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    raw_examples = []

def _format_example(ex):
    input_text = f"Articolo:\n\n{ex['article']}\n\nEvento: {ex['event']}\n\nSpan estratti: {json.dumps(ex['all_loc_span'], ensure_ascii=False)}"
    output_text = json.dumps(ex["output"], ensure_ascii=False)
    return {"input": input_text, "output": output_text}

example_prompt = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}"),
])

few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=[_format_example(ex) for ex in raw_examples],
)

full_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_PROMPT),
    few_shot_prompt,
    (
        "human",
        "Articolo:\n\n{article}\n\nEvento: {event_title}\n\nSpan estratti: {all_loc_span}"
    ),
])

structured_geo = structured_llm(extraction_llm, EventGeoExtraction)

MUNICIPALITIES_CSV = Path("data/italian_municipalities.csv")
COUNTRIES_CSV = Path("data/italian_provinces.csv")
REGIONS_CSV = Path("data/italian_regions.csv")


def _load_municipalities() -> dict[str, str]:
    municipalities: dict[str, str] = {}
    if MUNICIPALITIES_CSV.exists():
        with open(MUNICIPALITIES_CSV, encoding="latin-1") as f:
            for row in csv.DictReader(f, delimiter=";"):
                name = (row.get("Denominazione in italiano") or "").strip()
                county = ""
                for key in (
                    "Denominazione provincia",
                    "Denominazione Città metropolitana",
                    "Denominazione regione",
                ):
                    candidate = (row.get(key) or "").strip()
                    if candidate and candidate != "-":
                        county = candidate
                        break
                if name:
                    municipalities[name.lower()] = county or name
    return municipalities


def _load_counties() -> set[str]:
    counties: set[str] = set()
    if COUNTRIES_CSV.exists():
        with open(COUNTRIES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                province = (row.get("Province") or "").strip()
                region = (row.get("Region") or "").strip()
                if province:
                    counties.add(province.lower())
                if region:
                    counties.add(region.lower())
    if REGIONS_CSV.exists():
        with open(REGIONS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                region = (row.get("Region") or "").strip()
                if region:
                    counties.add(region.lower())
    return counties


_MUNICIPALITIES = _load_municipalities()
_COUNTIES = _load_counties()


def _resolve_deduced_county(place: dict) -> str | None:
    candidates = [
        place.get("city"),
        place.get("specific_name_place"),
        place.get("hamlet"),
        place.get("urban_zone"),
        place.get("address"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        key = str(candidate).strip().lower()
        if key in _MUNICIPALITIES:
            return _MUNICIPALITIES[key]
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate).strip()
        if value and value.lower() in _COUNTIES:
            return value
    return None


def _enrich_deduced_attributes(geo_data: dict, editorial_location: str) -> dict:
    """
    TODO: Inserire qui la logica di arricchimento / deduzione con tool esterni.
    Esempio:
    - Se 'urban_zone' = 'Prè' e 'city' è None -> imposta city = {'value': 'Genova', 'provenance': 'deduced'}
    - Se 'city' = 'Carpi' e 'county' è None -> imposta county = {'value': 'Modena', 'provenance': 'deduced'}

    Al momento gli attributi presenti nell'output dell'LLM vengono marcati come 'extracted'.
    Se il county non è estratto, lo si deduce dal file dei comuni italiani.
    """
    enriched = dict(geo_data)
    enriched_places = []
    for place in geo_data.get("places") or []:
        place_dict = dict(place) if isinstance(place, dict) else (place.model_dump() if hasattr(place, "model_dump") else {})
        enriched_place = {}
        for field_name, value in place_dict.items():
            if value is None or value == "":
                enriched_place[field_name] = None
            else:
                enriched_place[field_name] = {"value": value, "provenance": "extracted"}
        if not (place_dict.get("county") or "").strip():
            deduced_county = _resolve_deduced_county(place_dict)
            if deduced_county:
                enriched_place["county"] = {"value": deduced_county, "provenance": "deduced"}
        enriched_places.append(enriched_place)
    enriched["places"] = enriched_places
    return enriched


def geo_extractor(state: NewsArticleState) -> dict:
    print("\n========== GEO EXTRACTOR ==========")

    events = state.get("events") or []
    if not state.get("is_event") or not events:
        return {"events": events}

    enriched_events = []
    for ev in events:
        if not isinstance(ev, dict):
            enriched_events.append(ev)
            continue

        event_title = ev.get("title", "")
        all_loc_span = ev.get("all_loc_span", [])

        messages = full_prompt.format_messages(
            article=state["article"],
            event_title=event_title,
            all_loc_span=json.dumps(all_loc_span, ensure_ascii=False),
        )

        # 1. Estrazione strutturata dall'LLM (provenance="extracted")
        raw_geo: EventGeoExtraction = structured_geo.invoke(messages)
        geo_dict = raw_geo.model_dump()

        # 2. Arricchimento con tool esterni (provenance="deduced")
        enriched_geo = _enrich_deduced_attributes(
            geo_dict, state.get("editorial_location", "")
        )

        ev_updated = {**ev, "geo": enriched_geo}
        enriched_events.append(ev_updated)

    return {"events": enriched_events}