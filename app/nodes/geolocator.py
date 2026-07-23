import csv
from pathlib import Path

from geopy.geocoders import Nominatim

from app.models.event import Event


geolocator = Nominatim(user_agent="urban_events_agent")

PROVINCES_CSV = Path("data/italian_provinces.csv")
_valid_provinces: set[str] = set()

if PROVINCES_CSV.exists():
    with open(PROVINCES_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _valid_provinces.add(row["Province"].strip().lower())
            _valid_provinces.add(row["Abbreviation"].strip().lower())

REGIONS_CSV = Path("data/italian_regions.csv")
_valid_regions: set[str] = set()

if REGIONS_CSV.exists():
    with open(REGIONS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _valid_regions.add(row["Region"].strip().lower())


def _is_region(location: str) -> bool:
    normalized = location.strip().lower()
    return any(normalized == region.lower() for region in _valid_regions)


def _validate_region(location: str) -> str | None:
    normalized = location.strip().lower()
    for region in _valid_regions:
        if normalized == region.lower():
            return region
    return None


def _validate_county(county: str | None) -> str | None:
    if county is None:
        return None
    normalized = county.strip().lower().replace("-", " ")
    for valid in _valid_provinces:
        if normalized == valid.replace("-", " "):
            return county
    print(f"  County '{county}' not found in Italian provinces. Discarded.")
    return None


def _extract_city_from_address(address: dict) -> str | None:
    for key in ("city", "town", "village", "municipality", "county"):
        if address.get(key):
            return address[key]
    return None


def _cities_match(extracted: str, geocoded: str) -> bool:
    a = extracted.strip().lower()
    b = geocoded.strip().lower()
    return a == b or a in b or b in a


def _build_query(event, editorial_location: str) -> str:
    parts = []
    if event.street:
        parts.append(event.street)
    if event.place:
        parts.append(event.place)
    if event.county:
        parts.append(event.county)
    return ", ".join(parts) if parts else editorial_location


def _is_province(place: str) -> bool:
    normalized = place.strip().lower().replace("-", " ")
    for valid in _valid_provinces:
        if normalized == valid.replace("-", " "):
            return True
    return False


def _geocode_as_province(query: str) -> tuple[float, float, str] | None:
    results = geolocator.geocode(
        query,
        exactly_one=False,
        language="it",
        addressdetails=True,
        limit=5,
    )

    match = next((item for item in results if item.raw.get("addresstype") == "city"), None)
    if match:
        return match.latitude, match.longitude, match.address
    return None


def _geocode_and_match(query: str, place: str) -> tuple[float, float, str] | None:
    results = geolocator.geocode(
        query,
        exactly_one=False,
        language="it",
        addressdetails=True,
        limit=5,
    )

    for item in results or []:
        address = item.raw.get("address", {})
        location = address.get("village") or address.get("town") or address.get("city") or ""
        if _cities_match(place, location):
            return item.latitude, item.longitude, item.address

    for item in results or []:
        addresstype = item.raw.get("addresstype", "")
        address = item.raw.get("address", {})
        if addresstype in ("city", "town") or "city" in address or "town" in address:
            return item.latitude, item.longitude, item.address

    return None


def _geocode_place(query: str, place: str, editorial_location: str) -> tuple[float, float, str] | None:
    print(f"  Trying: '{query}'")
    match = _geocode_and_match(query, place)
    if match:
        return match

    query_with_location = f"{query}, {editorial_location}"
    print(f"  Trying: '{query_with_location}'")
    match = _geocode_and_match(query_with_location, place)
    if match:
        return match

    if query != place:
        print(f"  Trying: '{place}'")
        match = _geocode_and_match(place, place)
        if match:
            return match

        place_with_location = f"{place}, {editorial_location}"
        print(f"  Trying: '{place_with_location}'")
        match = _geocode_and_match(place_with_location, place)
        if match:
            return match

    return None


def _geocode_and_validate(query: str, expected_place: str) -> tuple[float, float, str] | None:
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

        if geocoded_city and _cities_match(expected_place, geocoded_city):
            return result.latitude, result.longitude, geocoded_city

    return None


def event_geolocator(state: dict) -> dict:
    print("\n========== GEO LOCATOR ==========")

    if state.get("event") is None:
        print("  No event. Skipping.")
        return {"event": None}

    event = state["event"]
    editorial_location = state.get("editorial_location")

    if not editorial_location:
        print("  Error: editorial_location is required but not provided.")
        return {"event": event}

    if not isinstance(event, Event):
        return {"event": event}

    if _is_region(editorial_location):
        print(f"  Flow: REGIONAL LOCATION ({editorial_location})")
        validated_region = _validate_region(editorial_location)
        if not validated_region:
            print(f"  Warning: '{editorial_location}' is not a valid Italian region.")

        query = _build_query(event, editorial_location)
        match = _geocode_place(query, event.place, editorial_location)
        if match:
            event.latitude, event.longitude, event.geocoded_city = match
            print(f"  Result: VALIDATED (region-level)")
        else:
            print(f"  Result: REJECTED (no match for query '{query}' in region '{editorial_location}')")
    else:
        event.county = _validate_county(event.county)

        if event.county:
            print(f"  Flow: COUNTY PRESENT ({event.county})")
            query = _build_query(event, editorial_location)
            match = _geocode_place(query, event.place, editorial_location)
            if match:
                event.latitude, event.longitude, event.geocoded_city = match
                print(f"  Result: VALIDATED")
            else:
                print(f"  Result: REJECTED (no match for query '{query}')")
        else:
            print(f"  Flow: NO COUNTY (place='{event.place}')")
            if _is_province(event.place):
                print(f"  Subflow: PLACE IS A PROVINCE")
                if event.street is not None:
                    query = _build_query(event, editorial_location)
                    print(f"  Trying street+place query: '{query}'")
                    match = _geocode_place(query, event.place, editorial_location)
                    if match:
                        event.latitude, event.longitude, event.geocoded_city = match
                        print(f"  Result: VALIDATED (via street+place)")
                        return {"event": event}

                print(f"  Trying province fallback")
                match = _geocode_as_province(event.place)
                if match:
                    event.latitude, event.longitude, event.geocoded_city = match
                    print(f"  Result: VALIDATED (via province fallback)")
                else:
                    print(f"  Result: REJECTED (no match)")
            else:
                query = _build_query(event, editorial_location)
                print(f"  Subflow: STANDARD PLACE (query='{query}')")
                match = _geocode_place(query, event.place, editorial_location)
                if match:
                    event.latitude, event.longitude, event.geocoded_city = match
                    print(f"  Result: VALIDATED")
                else:
                    print(f"  Result: REJECTED (no match)")

    return {"event": event}
