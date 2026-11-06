from typing import Optional
from pydantic import BaseModel, Field


class EventDate(BaseModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None


class Event(BaseModel):
    category: str
    place: str
    county: Optional[str] = None
    street: Optional[str] = None
    loc_description: Optional[str] = None

    start_date: EventDate
    end_date: Optional[EventDate] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocoded_city: Optional[str] = None
    extracted_info: Optional[dict[str, str]] = None
