import json
import time
import argparse
from pathlib import Path

from app.graph import graph
from app.timing import clear_timing_log, record_timing


def process_articles(input_file: str, output_file: str):
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"Input file {input_path} not found.")
        return

    clear_timing_log()

    with open(input_path, encoding="utf-8") as f:
        items = json.load(f, strict=False)

    items = items[:2]

    results = []

    for i, item in enumerate(items, 1):
        print(f"\n[{i}/{len(items)}] Processing: {item['news text'][:80]}...")

        article_start = time.time()

        state = graph.invoke(
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

        article_duration = time.time() - article_start
        record_timing("total_article", article_duration, i)
        print(f"  [total_article] {article_duration:.3f}s")

        entry = {
            "url": item["url"],
            "title": item.get("title") or "",
            "subtitle": item.get("subtitle") or "",
            "article": item["news text"],
            "publication_date": item["publication date"],
            "is_event": state.get("is_event"),
            "events": state.get("events"),
            "multi_event": state.get("multi_event"),
        }

        results.append(entry)

        print(f"  -> is_event={entry['is_event']}")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(results)} articles processed. Output: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process urban events")
    parser.add_argument("-i", "--input", default="data/data.json", help="Input JSON file")
    parser.add_argument("-o", "--output", default="data/results.json", help="Output JSON file")
    args = parser.parse_args()

    process_articles(args.input, args.output)
