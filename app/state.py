from typing import Optional
from typing_extensions import TypedDict

from app.models.event import Event


class EventState(TypedDict):
    article: str
    publication_date: str
    is_event: Optional[bool]
    event: Optional[Event]