import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from app.llm import extraction_llm, structured_llm
from app.models.temporal_extractor import TemporalExtractionResult
from app.state import EventState


SYSTEM_PROMPT = Path("app/prompts/temporal_extractor.txt").read_text(encoding="utf-8")

full_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Articolo:\n\n{article}"),
])

structured_temporal = structured_llm(extraction_llm, TemporalExtractionResult)


def event_temporal_extractor(state: EventState):
    print("\n========== TEMPORAL EXTRACTOR ==========")

    events = state.get("events") or []
    enriched_events = []

    for ev in events:
        messages = full_prompt.format_messages(article=state["article"])
        response = structured_temporal.invoke(messages)
        spans = list(response.spans or [])
        enriched_events.append(
            {**ev, "temporal_spans": spans} if isinstance(ev, dict) else ev
        )

    return {"events": enriched_events}
