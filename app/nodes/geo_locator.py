from typing import Any, Optional
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="urban_events_agent_v2")


def _extract_val(field: Optional[dict | Any]) -> Optional[str]:
    """Estrae il valore stringa da un campo che può essere un dict {'value': ..., 'provenance': ...} o un oggetto Pydantic/None."""
    if not field:
        return None
    if isinstance(field, dict):
        return field.get("value")
    if hasattr(field, "value"):
        return field.value
    return str(field) if field else None


def _clean_display_name(full_address: str, address_details: dict) -> str:
    """Tronca l'indirizzo fino al livello della provincia (inclusa)."""
    parts = [p.strip() for p in full_address.split(",") if p.strip()]
    if not parts:
        return full_address

    county = address_details.get("county") or address_details.get("state_district")
    if not county:
        return full_address

    clean_county = county.replace("Provincia di ", "").strip().lower()

    truncated_parts = []
    for part in parts:
        truncated_parts.append(part)
        clean_part = part.replace("Provincia di ", "").strip().lower()
        if clean_part == clean_county:
            break

    return ", ".join(truncated_parts)


def _geocode_explicit(
    street: Optional[str] = None,
    city: Optional[str] = None,
    county: Optional[str] = None,
    country: str = "Italia",
) -> Optional[tuple[float, float, str, dict, Any, Any]]:
    """Chiamata esplicita strutturata a Nominatim."""
    query_dict = {"country": country}
    if street:
        query_dict["street"] = street
    if city:
        query_dict["city"] = city
    if county:
        query_dict["county"] = county

    try:
        results = geolocator.geocode(
            query_dict,
            exactly_one=True,
            language="it",
            addressdetails=True,
        )
        if results:
            raw = results.raw
            return (
                results.latitude,
                results.longitude,
                results.address,
                raw.get("address", {}),
                raw.get("osm_id"),
                raw.get("osm_type"),
            )
    except Exception as e:
        print(f"  [WARN] Explicit geocoding failed for {query_dict}: {e}")
    return None


def _geocode_freeform(
    query_str: str,
) -> Optional[tuple[float, float, str, dict, Any, Any]]:
    """Fallback a ricerca libera per luoghi specifici o quartieri."""
    try:
        results = geolocator.geocode(
            query_str,
            exactly_one=True,
            language="it",
            addressdetails=True,
            country_codes="it",
        )
        if results:
            raw = results.raw
            return (
                results.latitude,
                results.longitude,
                results.address,
                raw.get("address", {}),
                raw.get("osm_id"),
                raw.get("osm_type"),
            )
    except Exception as e:
        print(f"  [WARN] Freeform geocoding failed for '{query_str}': {e}")
    return None


def geocode_location_item(
    place: dict, editorial_location: str
) -> tuple[Optional[dict], dict]:
    """Geolocalizza un singolo LocationItem basandosi direttamente sui campi estratti."""
    city = _extract_val(place.get("city"))
    hamlet = _extract_val(place.get("hamlet"))
    urban_zone = _extract_val(place.get("urban_zone"))
    county = _extract_val(place.get("county"))
    address = _extract_val(place.get("address"))
    specific_place = _extract_val(place.get("specific_name_place"))

    target_city = city or hamlet or editorial_location
    deduced_updates = {}
    res = None

    if address:
        res = _geocode_explicit(street=address, city=target_city, county=county)

    if not res and (specific_place or urban_zone):
        loc_name = specific_place or urban_zone
        res = _geocode_freeform(f"{loc_name}, {target_city}")

    if not res and hamlet:
        res = _geocode_explicit(city=hamlet, county=county)

    if not res and target_city:
        res = _geocode_explicit(city=target_city, county=county)

    if res:
        lat, lon, full_address, address_details, osm_id, osm_type = res

        display_name = _clean_display_name(full_address, address_details)

        geo_point = {
            "latitude": lat,
            "longitude": lon,
            "display_name": display_name,
            "raw_display_name": full_address,
            "osm_id": osm_id,
            "osm_type": osm_type,
        }

        geocoded_county = address_details.get("county") or address_details.get(
            "state_district"
        )
        geocoded_city = (
            address_details.get("city")
            or address_details.get("town")
            or address_details.get("village")
        )

        if not county and geocoded_county:
            clean_county = geocoded_county.replace("Provincia di ", "").strip()
            deduced_updates["county"] = {
                "value": clean_county,
                "provenance": "deduced",
            }

        if not city and geocoded_city:
            deduced_updates["city"] = {
                "value": geocoded_city,
                "provenance": "deduced",
            }

        return geo_point, deduced_updates

    return None, {}


def geo_locator(state: dict) -> dict:
    print("\n========== GEO LOCATOR ==========")

    events = state.get("events") or []
    if not state.get("is_event") or not events:
        print("  No event found. Skipping geolocator.")
        return {"events": events}

    editorial_location = state.get("editorial_location", "")
    enriched_events = []

    for ev in events:
        if not isinstance(ev, dict):
            enriched_events.append(ev)
            continue

        geo_data = ev.get("geo") or {}
        places = geo_data.get("places") or []

        geocoded_places = []
        for place in places:
            geo_point, deduced_updates = geocode_location_item(
                place, editorial_location
            )

            updated_place = dict(place)
            for k, v in deduced_updates.items():
                if not updated_place.get(k):
                    updated_place[k] = v

            if geo_point:
                updated_place["coordinates"] = geo_point

            geocoded_places.append(updated_place)

        geo_data["places"] = geocoded_places
        ev_updated = {**ev, "geo": geo_data}
        enriched_events.append(ev_updated)

    return {"events": enriched_events}