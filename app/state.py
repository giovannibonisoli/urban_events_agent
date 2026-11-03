from typing import Optional
from typing_extensions import TypedDict


class NewsArticleState(TypedDict):
    article: str
    article_title: Optional[str]
    article_subtitle: Optional[str]
    publication_date: str
    editorial_location: str
    is_event: Optional[bool]
    events: Optional[list]
    multi_event: Optional[str]
