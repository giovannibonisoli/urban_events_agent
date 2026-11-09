from langgraph.graph import StateGraph, START, END

from app.state import NewsArticleState
from app.nodes import (
    event_detector,
    event_classifier,
    event_temporal_extractor,
    date_extractor,
    geo_extractor,
    geo_span_extractor,
    geo_locator
)
from app.timing import timed_node


def _after_detector(state: NewsArticleState) -> str:
    if not state.get("is_event"):
        return "end"
    return "classifier"


builder = StateGraph(NewsArticleState)

builder.add_node("detector", timed_node(event_detector))
builder.add_node("classifier", timed_node(event_classifier))
builder.add_node("temporal_extractor", timed_node(event_temporal_extractor))
builder.add_node("date_extractor", timed_node(date_extractor))
builder.add_node("geo_span_extractor", timed_node(geo_span_extractor))
builder.add_node("geo_extractor", timed_node(geo_extractor))
builder.add_node("geo_locator", timed_node(geo_locator))

builder.add_edge(START, "detector")
builder.add_conditional_edges("detector", _after_detector, {"classifier": "classifier", "end": END})
builder.add_edge("classifier", "temporal_extractor")
builder.add_edge("temporal_extractor", "date_extractor")
builder.add_edge("date_extractor", "geo_span_extractor")
builder.add_edge("geo_span_extractor", "geo_extractor")
builder.add_edge("geo_extractor", "geo_locator")
builder.add_edge("geo_locator", END)

graph = builder.compile()
