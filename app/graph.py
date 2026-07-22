from langgraph.graph import StateGraph, START, END

from app.state import EventState
from app.nodes import event_detector, event_classifier, geo_extractor, date_extractor, event_geolocator, info_extractor
from app.timing import timed_node


def _after_detector(state: EventState) -> str:
    if not state.get("is_event"):
        return "end"
    return "classifier"


def _after_classifier(state: EventState) -> str:
    if state.get("event_category") == "Altro":
        return "end"
    return "geo_extractor"


builder = StateGraph(EventState)

# Nodes with timing
builder.add_node("detector", timed_node(event_detector))
builder.add_node("classifier", timed_node(event_classifier))
builder.add_node("geo_extractor", timed_node(geo_extractor))
builder.add_node("date_extractor", timed_node(date_extractor))
builder.add_node("geolocator", timed_node(event_geolocator))
builder.add_node("info_extractor", timed_node(info_extractor))

# Edges
builder.add_edge(START, "detector")
builder.add_conditional_edges("detector", _after_detector, {"classifier": "classifier", "end": END})
builder.add_conditional_edges("classifier", _after_classifier, {"geo_extractor": "geo_extractor", "end": END})
builder.add_edge("geo_extractor", "date_extractor")
builder.add_edge("date_extractor", "geolocator")
builder.add_edge("geolocator", "info_extractor")
builder.add_edge("info_extractor", END)

# Compile graph
graph = builder.compile()
