import json
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate

from app.llm import extraction_llm, structured_llm
from app.models.temporal_extractor import TemporalExtractionResult
from app.state import NewsArticleState


SYSTEM_PROMPT = Path("app/prompts/temporal_extractor.txt").read_text(encoding="utf-8")

with open("app/prompts/examples/temporal_extractor_examples.json", encoding="utf-8") as f:
    raw_examples = json.load(f)


def _format_example(ex):
    input_text = f"Evento da analizzare: {ex['event_title']}\n\nArticolo:\n\n{ex['article']}"
    output_text = json.dumps({"spans": ex.get("spans", [])}, ensure_ascii=False)
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
    ("human", "Evento da analizzare: {event_title}\n\nArticolo:\n\n{article}"),
])

structured_temporal = structured_llm(extraction_llm, TemporalExtractionResult)


def event_temporal_extractor(state: NewsArticleState):
    print("\n========== TEMPORAL EXTRACTOR ==========")

    events = state.get("events") or []
    enriched_events = []

    for ev in events:
        event_title = ev.get("title", "") if isinstance(ev, dict) else ""
        messages = full_prompt.format_messages(
            article=state["article"],
            event_title=event_title,
        )
        response = structured_temporal.invoke(messages)
        spans = list(response.spans or [])
        enriched_events.append(
            {**ev, "temporal_spans": spans} if isinstance(ev, dict) else ev
        )

    return {"events": enriched_events}
