from pydantic import BaseModel


class DetectionResult(BaseModel):
    is_event: bool