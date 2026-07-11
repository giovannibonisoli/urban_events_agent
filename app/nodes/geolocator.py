from geopy.geocoders import Nominatim

from app.models.event import Event


geolocator = Nominatim(user_agent="urban_events_agent")


def _extract_city_from_address(address: dict) -> str | None:
    for key in ("city", "town", "village", "municipality", "county"):
        if address.get(key):
            return address[key]
    return None


def _cities_match(extracted: str, geocoded: str) -> bool:
    a = extracted.strip().lower()
    b = geocoded.strip().lower()
    return a == b or a in b or b in a


def _geocode_and_validate(query: str, expected_city: str) -> tuple[float, float, str] | None:
    results = geolocator.geocode(
        query,
        exactly_one=False,
        language="it",
        addressdetails=True,
        limit=5,
    )

    for result in results or []:
        address = result.raw.get("address", {})
        geocoded_city = _extract_city_from_address(address)

        if geocoded_city and _cities_match(expected_city, geocoded_city):
            return result.latitude, result.longitude, geocoded_city

    return None


def event_geolocator(state: dict) -> dict:
    if state.get("event") is None:
        return {"event": None}

    event = state["event"]
    if not isinstance(event, Event):
        return {"event": event}

    if event.location:
        match = _geocode_and_validate(f"{event.location}, {event.city}", event.city)
        if match:
            event.latitude, event.longitude, event.geocoded_city = match
            return {"event": event}

    match = _geocode_and_validate(event.city, event.city)
    if match:
        event.latitude, event.longitude, event.geocoded_city = match

    return {"event": event}
