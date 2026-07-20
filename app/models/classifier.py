from pydantic import BaseModel


class ClassificationResult(BaseModel):
    event_category: str
    is_event: bool
