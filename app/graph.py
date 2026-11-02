from langgraph.graph import StateGraph, START, END

from app.state import NewsArticleState
from app.nodes import event_detector, event_classifier, date_extractor, event_temporal_extractor
from app.timing import timed_node


def _after_detector(state: NewsArticleState) -> str:
    if not state.get("is_event"):
        return "end"
    return "classifier"


def _after_classifier(state: NewsArticleState) -> str:
    # TEMPORARILY STOPPED AFTER THE DATE EXTRACTOR: next step would be the geolocator.
    # For now: step to the temporal extractor after the classifier.
    return "temporal_extractor"


builder = StateGraph(NewsArticleState)

builder.add_node("detector", timed_node(event_detector))
builder.add_node("classifier", timed_node(event_classifier))
builder.add_node("temporal_extractor", timed_node(event_temporal_extractor))
builder.add_node("date_extractor", timed_node(date_extractor))

builder.add_edge(START, "detector")
builder.add_conditional_edges("detector", _after_detector, {"classifier": "classifier", "end": END})
builder.add_edge("classifier", "temporal_extractor")
builder.add_edge("temporal_extractor", "date_extractor")
builder.add_edge("date_extractor", END)

graph = builder.compile()
