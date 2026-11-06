from typing import Optional
from pydantic import BaseModel, Field


class EventDate(BaseModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None
