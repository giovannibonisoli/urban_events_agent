import json
from pathlib import Path

from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate

from app.llm import extraction_llm, structured_llm
from app.models.event import _GeoExtraction
from app.state import EventState


SYSTEM_PROMPT = Path("app/prompts/geo_extractor.txt").read_text(encoding="utf-8")

with open("app/prompts/examples/geo_extractor_examples.json", encoding="utf-8") as f:
    raw_examples = json.load(f)


def _format_example(ex):
    input_text = f"Articolo:\n\n{ex['article']}"
    output_text = json.dumps({
        "place": ex["place"],
        "county": ex.get("county"),
        "street": ex.get("street"),
        "loc_description": ex.get("loc_description"),
    }, ensure_ascii=False)
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
    ("human", "Articolo:\n\n{article}"),
])

structured_geo = structured_llm(extraction_llm, _GeoExtraction)


def geo_extractor(state: EventState) -> dict:
    print("\n========== GEO EXTRACTOR ==========")

    if not state["is_event"]:
        print("No event found. Skipping extraction.")
        return {"geo": None}

    messages = full_prompt.format_messages(article=state["article"])
    raw = structured_geo.invoke(messages)

    print("Extracted Geo:")
    print(raw)

    return {"geo": raw}
