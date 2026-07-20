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
    lines = [
        f"event_category = {ex['event_category']}",
        f"is_event = {'true' if ex['is_event'] else 'false'}",
    ]
    output_text = "\n".join(lines)
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

structured_classifier = structured_llm(detection_llm, ClassificationResult)


def event_classifier(state: EventState):

    print("\n========== EVENT CLASSIFIER ==========")

    messages = full_prompt.format_messages(article=state["article"])
    response = structured_classifier.invoke(messages)

    print(response)

    return {
        "event_category": response.event_category,
        "is_event": response.is_event,
    }
