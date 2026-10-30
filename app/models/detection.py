from pydantic import BaseModel


class EventItem(BaseModel):
    title: str = ""
    is_main: bool = False


class DetectionResult(BaseModel):
    events: list[EventItem] = []
