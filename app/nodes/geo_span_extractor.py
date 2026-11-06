import json
from pathlib import Path
from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)

from app.llm import extraction_llm, structured_llm
from app.models.geo import GeoSpanExtractionResult
from app.state import NewsArticleState

SYSTEM_PROMPT = Path("app/prompts/geo_span_extractor.txt").read_text(encoding="utf-8")

try:
    with open("app/prompts/examples/geo_span_examples.json", encoding="utf-8") as f:
        raw_examples = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    raw_examples = []

def _format_example(ex):
    input_text = f"Articolo:\n\n{ex['article']}\n\nEvento da analizzare: {ex['event']}"
    output_text = json.dumps({"all_loc_span": ex["all_loc_span"]}, ensure_ascii=False)
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
    ("human", "Articolo:\n\n{article}\n\nEvento da analizzare: {event_title}"),
])

structured_geo_span = structured_llm(extraction_llm, GeoSpanExtractionResult)

def geo_span_extractor(state: NewsArticleState) -> dict:
    print("\n========== GEO SPAN EXTRACTOR ==========")

    events = state.get("events") or []
    if not state.get("is_event") or not events:
        return {"events": events}

    enriched_events = []
    for ev in events:
        if not isinstance(ev, dict):
            enriched_events.append(ev)
            continue

        event_title = ev.get("title", "")
        messages = full_prompt.format_messages(
            article=state["article"], event_title=event_title
        )

        response: GeoSpanExtractionResult = structured_geo_span.invoke(messages)
        ev_updated = {**ev, "all_loc_span": response.all_loc_span}
        enriched_events.append(ev_updated)

    return {"events": enriched_events}