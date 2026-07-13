from langgraph.graph import StateGraph, START, END

from app.state import EventState
from app.nodes import event_detector, geo_extractor, date_extractor, event_geolocator


builder = StateGraph(EventState)

# Nodes
builder.add_node("detector", event_detector)
builder.add_node("geo_extractor", geo_extractor)
builder.add_node("date_extractor", date_extractor)
builder.add_node("geolocator", event_geolocator)

# Edges
builder.add_edge(START, "detector")
builder.add_edge("detector", "geo_extractor")
builder.add_edge("geo_extractor", "date_extractor")
builder.add_edge("date_extractor", "geolocator")
builder.add_edge("geolocator", END)

# Compile graph
graph = builder.compile()