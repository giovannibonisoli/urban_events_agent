import json
import argparse
from pathlib import Path

from app.graph import graph
from app.classifier_graph import classifier_graph


DATA_FILE = Path("data/data.json")


def main():
    parser = argparse.ArgumentParser(description="Process urban events")
    parser.add_argument(
        "--graph",
        choices=["detector", "classifier"],
        default="detector",
        help="Graph to use: 'detector' (binary detection) or 'classifier' (categorized classification)",
    )
    args = parser.parse_args()

    g = classifier_graph if args.graph == "classifier" else graph

    if not DATA_FILE.exists():
        print(f"File {DATA_FILE} not found.")
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        items = json.load(f)

    for i, item in enumerate(items, 1):
        print("\n" + "=" * 80)
        print(f"ITEM: {i}")
        print("=" * 80)

        result = g.invoke(
            {
                "article": item["news text"],
                "publication_date": item["publication date"],
                "is_event": None,
                "event_category": None,
                "geo": None,
                "event": None,
                "extracted_info": None,
            }
        )

        print("\n=== FINAL STATE ===")
        print(result)

        if args.graph == "classifier":
            print(f"\n  Category: {result.get('event_category', 'N/A')}")

        print("\n=== EVENT ===")
        print(result["event"])

        extracted = result.get("extracted_info")
        if extracted:
            print(f"\n=== EXTRACTED INFO ===")
            for k, v in extracted.items():
                print(f"  {k}: {v}")

        event = result.get("event")
        if event:
            print(f"\n=== GEOLOCATION ===")
            print(f"  Place:     {event.place}")
            print(f"  County:    {event.county or 'N/A'}")
            print(f"  Street:    {event.street or 'N/A'}")
            print(f"  LocDescription: {event.loc_description or 'N/A'}")
            print(f"  Geocoded:  {event.geocoded_city or 'N/A'}")
            if event.latitude and event.longitude:
                print(f"  Status: VALIDATED")
                print(f"  Lat: {event.latitude}, Lng: {event.longitude}")
                print(f"  Google Maps: https://www.google.com/maps?q={event.latitude},{event.longitude}")
            else:
                print(f"  Status: REJECTED (no match found)")


if __name__ == "__main__":
    main()