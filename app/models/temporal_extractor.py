from pydantic import BaseModel


class TemporalExtractionResult(BaseModel):
    spans: list[str] = []
