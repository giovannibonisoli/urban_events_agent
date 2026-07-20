from langgraph.graph import StateGraph, START, END

from app.state import EventState
from app.nodes import event_classifier, geo_extractor, date_extractor, event_geolocator, info_extractor


def _after_classifier(state: EventState) -> str:
    if not state.get("is_event") or state.get("event_category") == "Altro":
        return "end"
    return "geo_extractor"


builder = StateGraph(EventState)

# Nodes
builder.add_node("classifier", event_classifier)
builder.add_node("geo_extractor", geo_extractor)
builder.add_node("date_extractor", date_extractor)
builder.add_node("geolocator", event_geolocator)
builder.add_node("info_extractor", info_extractor)

# Edges
builder.add_edge(START, "classifier")
builder.add_conditional_edges("classifier", _after_classifier, {"geo_extractor": "geo_extractor", "end": END})
builder.add_edge("geo_extractor", "date_extractor")
builder.add_edge("date_extractor", "geolocator")
builder.add_edge("geolocator", "info_extractor")
builder.add_edge("info_extractor", END)

# Compile graph
classifier_graph = builder.compile()
