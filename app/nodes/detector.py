from app.state import EventState


from pathlib import Path

from app.llm import detection_llm
from app.models.detection import DetectionResult


PROMPT = Path("app/prompts/detector.txt").read_text(encoding="utf-8")

structured_llm = detection_llm.with_structured_output(DetectionResult)


def event_detector(state: EventState):

    print("\n========== EVENT DETECTOR ==========")

    response = structured_llm.invoke(
        f"""{PROMPT}

Articolo:

{state["article"]}
"""
    )

    print(response)

    return {
        "is_event": response.is_event
    }