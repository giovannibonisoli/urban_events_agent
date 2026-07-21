import json
from pathlib import Path

from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate

from app.llm import detection_llm, structured_llm
from app.models.detection import DetectionResult
from app.state import EventState


SYSTEM_PROMPT = Path("app/prompts/detector.txt").read_text(encoding="utf-8")

with open("app/prompts/examples/detector_examples.json", encoding="utf-8") as f:
    raw_examples = json.load(f)


def _format_example(ex):
    input_text = f"Articolo:\n\n{ex['article']}"
    output_text = json.dumps({"is_event": ex["is_event"]})
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

structured_detector = structured_llm(detection_llm, DetectionResult)


def event_detector(state: EventState):

    print("\n========== EVENT DETECTOR ==========")

    messages = full_prompt.format_messages(article=state["article"])
    response = structured_detector.invoke(messages)

    print(response)

    return {
        "is_event": response.is_event
    }
