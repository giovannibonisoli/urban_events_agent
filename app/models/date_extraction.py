from typing import Optional

from pydantic import BaseModel, Field

from app.models.event import EventDate


class StartDateExtraction(BaseModel):
    start_date: EventDate = Field(default_factory=EventDate)


class EndDateExtraction(BaseModel):
    end_date: EventDate = Field(default_factory=EventDate)


class _DateExtraction(BaseModel):
    start_date: EventDate = Field(default_factory=EventDate)
    end_date: Optional[EventDate] = None
