from pydantic import BaseModel


class ClassificationResult(BaseModel):
    event_category: str
