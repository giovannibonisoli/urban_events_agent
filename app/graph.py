from langgraph.graph import StateGraph, START, END

from app.state import EventState
from app.nodes import event_detector, event_extractor, event_geolocator


builder = StateGraph(EventState)

# Nodes
builder.add_node("detector", event_detector)
builder.add_node("extractor", event_extractor)
builder.add_node("geolocator", event_geolocator)

# Edges
builder.add_edge(START, "detector")
builder.add_edge("detector", "extractor")
builder.add_edge("extractor", "geolocator")
builder.add_edge("geolocator", END)

# Compile graph
graph = builder.compile()