from langgraph.graph import StateGraph, START, END

from app.state import EventState
from app.nodes import event_classifier, geo_extractor, date_extractor, event_geolocator


builder = StateGraph(EventState)

# Nodes
builder.add_node("classifier", event_classifier)
builder.add_node("geo_extractor", geo_extractor)
builder.add_node("date_extractor", date_extractor)
builder.add_node("geolocator", event_geolocator)

# Edges
builder.add_edge(START, "classifier")
builder.add_edge("classifier", "geo_extractor")
builder.add_edge("geo_extractor", "date_extractor")
builder.add_edge("date_extractor", "geolocator")
builder.add_edge("geolocator", END)

# Compile graph
classifier_graph = builder.compile()
