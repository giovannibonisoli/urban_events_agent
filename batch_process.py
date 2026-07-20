import json
import argparse
from pathlib import Path

from app.graph import graph
from app.classifier_graph import classifier_graph


def process_articles(input_file: str, output_file: str, use_classifier: bool):
    input_path = Path(input_file)
    output_path = Path(output_file)

    g = classifier_graph if use_classifier else graph

    if not input_path.exists():
        print(f"Input file {input_path} not found.")
        return

    with open(input_path, encoding="utf-8") as f:
        items = json.load(f)

    results = []

    for i, item in enumerate(items, 1):
        print(f"\n[{i}/{len(items)}] Processing: {item['news text'][:80]}...")

        state = g.invoke(
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

        event = state.get("event")
        entry = {
            "article": item["news text"],
            "publication_date": item["publication date"],
            "is_event": state.get("is_event"),
            "event_category": state.get("event_category"),
            "extracted_info": state.get("extracted_info"),
        }

        if event:
            entry["event"] = {
                "category": event.category,
                "place": event.place,
                "county": event.county,
                "street": event.street,
                "loc_description": event.loc_description,
                "start_date": {
                    "day": event.start_date.day,
                    "month": event.start_date.month,
                    "year": event.start_date.year,
                },
                "end_date": {
                    "day": event.end_date.day,
                    "month": event.end_date.month,
                    "year": event.end_date.year,
                } if event.end_date else None,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "geocoded_city": event.geocoded_city,
                "extracted_info": event.extracted_info,
            }
        else:
            entry["event"] = None

        results.append(entry)
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
        else:
            print(f"  -> is_event={entry['is_event']}, place=N/A")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(results)} articles processed. Output: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process urban events")
    parser.add_argument("-i", "--input", default="data/data.json", help="Input JSON file")
    parser.add_argument("-o", "--output", default="data/results.json", help="Output JSON file")
    parser.add_argument(
        "--graph",
        choices=["detector", "classifier"],
        default="detector",
        help="Graph to use: 'detector' (binary detection) or 'classifier' (categorized classification)",
    )
    args = parser.parse_args()

    process_articles(args.input, args.output, use_classifier=(args.graph == "classifier"))
