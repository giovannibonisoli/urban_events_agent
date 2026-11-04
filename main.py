import json
from pathlib import Path

from app.graph import graph


DATA_FILE = Path("data/data.json")


def main():
    if not DATA_FILE.exists():
        print(f"File {DATA_FILE} not found.")
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        items = json.load(f, strict=False)

    for i, item in enumerate(items, 1):
        print("\n" + "=" * 80)
        print(f"ITEM: {i}")
        print("=" * 80)

        result = graph.invoke(
            {
                "url": item["url"],
                "article": item["news text"],
                "article_title": item.get("title") or "",
                "article_subtitle": item.get("subtitle") or "",
                "publication_date": item["publication date"],
                "editorial_location": item["editorial_location"],
                "is_event": None,
                "events": None,
                "multi_event": None,
            }
        )

        print("\n=== FINAL STATE ===")
        print(result)

        # Temporary save
        with open("data/main_results.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "url": item["url"],
                    "is_event": result.get("is_event"),
                    "events": result.get("events"),
                    "multi_event": result.get("multi_event"),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )


if __name__ == "__main__":
    main()
