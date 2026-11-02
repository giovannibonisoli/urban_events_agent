import json
from pathlib import Path

from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate

from app.llm import detection_llm, structured_llm
from app.models.classifier import ClassificationResult
from app.state import EventState


SYSTEM_PROMPT = Path("app/prompts/classifier.txt").read_text(encoding="utf-8")

with open("app/prompts/examples/classifier_examples.json", encoding="utf-8") as f:
    raw_examples = json.load(f)


def _format_example(ex):
    input_text = f"Articolo:\n\n{ex['article']}"
    output_text = json.dumps({"event_category": ex["event_category"]}, ensure_ascii=False)
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
    ("system", SYSTEM_PROMPT),
    few_shot_prompt,
    ("human", "Articolo:\n\n{article}\n\nEvento da classificare: {event_title}"),
])

structured_classifier = structured_llm(detection_llm, ClassificationResult)


def event_classifier(state: EventState):
    print("\n========== EVENT CLASSIFIER ==========")

    events = state.get("events") or []

    event_categories: list[str] = []
    for ev in events:
        event_title = ev.get("title", "") if isinstance(ev, dict) else ""
        messages = full_prompt.format_messages(article=state["article"], event_title=event_title)
        response = structured_classifier.invoke(messages)
        event_categories.append(response.event_category)

    event_category = "Altro"
    if events and event_categories:
        main_event = next((e for e in events if e.get("is_main")), None)
        if main_event is None:
            main_event = events[0]
        main_idx = next((i for i, e in enumerate(events) if e is main_event), 0)
        event_category = event_categories[main_idx] if event_categories else "Altro"

    enriched_events = [
        {**ev, "event_category": cat} if isinstance(ev, dict) else ev
        for ev, cat in zip(events, event_categories)
    ]

    return {
        "events": enriched_events,
    }
