from typing import Optional
from typing_extensions import TypedDict

from app.models.event import Event, _GeoExtraction


class EventState(TypedDict):
    article: str
    publication_date: str
    is_event: Optional[bool]
    event_category: Optional[str]
    geo: Optional[_GeoExtraction]
    event: Optional[Event]