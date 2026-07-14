from app.state import EventState


from pathlib import Path

from app.llm import detection_llm, structured_llm
from app.models.detection import DetectionResult


PROMPT = Path("app/prompts/detector.txt").read_text(encoding="utf-8")

structured_detector = structured_llm(detection_llm, DetectionResult)


def event_detector(state: EventState):

    print("\n========== EVENT DETECTOR ==========")

    response = structured_detector.invoke(
        f"""{PROMPT}

Articolo:

{state["article"]}
"""
    )

    print(response)

    return {
        "is_event": response.is_event
    }