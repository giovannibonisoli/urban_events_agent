import json
from typing import Any
from pydantic import BaseModel, field_validator


class EventItem(BaseModel):
  title: str = ""
  is_main: bool = False


class DetectionResult(BaseModel):
  events: list[EventItem] = []

  @field_validator("events", mode="before")
  @classmethod
  def parse_events(cls, v: Any) -> Any:
    if isinstance(v, str):
      v_str = v.strip()
      if v_str.startswith("[") and v_str.endswith("]"):
        try:
          return json.loads(v_str)
        except json.JSONDecodeError:
          return []
    return v