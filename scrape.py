import json
import time
import re
import httpx
from bs4 import BeautifulSoup, Comment
from pathlib import Path
from pydantic import BaseModel

from app.llm import _make_llm, _load_config, structured_llm
from app.timing import record_timing, clear_timing_log


class ArticleLink(BaseModel):
    title: str = ""
    link: str = ""
    date: str = ""


class LinkExtractionResult(BaseModel):
    results: list[ArticleLink] = []


class ArticleExtraction(BaseModel):
    title: str = ""
    text: str = ""
    publication_date: str = ""


def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'img', 'picture', 'figure', 'svg']):
        tag.decompose()

    for tag in soup.find_all(class_=['image', 'gallery', 'slider', 'carousel', 'media']):
        tag.decompose()

    text = str(soup)

    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\r+', ' ', text)
    text = re.sub(r'\t+', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r' +\.', '.', text)
    text = re.sub(r' +,', ',', text)
    text = re.sub(r' +:', ':', text)
    text = re.sub(r' +;', ';', text)

    return text.strip()


def extract_links(html_content, llm):
    clean = clean_html(html_content)

    prompt = f"""Extract the list of news article links from this search results page.

Find all result items that represent news articles. Each result should have:
- A title (the headline text)
- A link (the URL to the article)
- A date (if available, otherwise empty string)

HTML:
{clean}"""

    print("  Invoking LLM for link extraction...")
    response = llm.invoke(prompt)
    return response


def extract_article(html_content, llm):
    clean = clean_html(html_content)

    prompt = f"""Extract data from this news article HTML.
Return the title, the full text, and the publication date.

HTML:
{clean}"""

    print("  Invoking LLM for article extraction...")
    response = llm.invoke(prompt)
    return response


def parse_json(text):
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        text = json_match.group(1)
    else:
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            text = brace_match.group(0)

    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return json.loads(text, strict=False)


def fetch_html(url):
    print(f"  Downloading: {url}")
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape newspaper: extract links then articles")
    parser.add_argument("url", help="Newspaper search/listing page URL")
    parser.add_argument("-o", "--output", default="data/scraped_articles.json", help="Output JSON file")
    parser.add_argument("--max-articles", type=int, default=10, help="Max articles to process")
    args = parser.parse_args()

    clear_timing_log()

    cfg = _load_config()["llm"]
    scraper_model = cfg["scraper_model"]

    print(f"Provider: {cfg['provider']}")
    print(f"Scraper model: {scraper_model}")

    llm = _make_llm(scraper_model)
    structured_link_llm = structured_llm(llm, LinkExtractionResult)
    structured_article_llm = structured_llm(llm, ArticleExtraction)

    total_start = time.time()

    # STEP 1: Fetch listing page and extract article links
    print("\n" + "=" * 60)
    print("STEP 1: Extracting article links")
    print("=" * 60)

    step1_start = time.time()
    listing_html = fetch_html(args.url)
    print(f"  Page downloaded: {len(listing_html)} chars")

    links_result = extract_links(listing_html, structured_link_llm)
    step1_duration = time.time() - step1_start
    record_timing("step1_link_extraction", step1_duration)
    print(f"  [step1_link_extraction] {step1_duration:.3f}s")

    from urllib.parse import urljoin
    base_url = args.url.split("/search")[0].split("/query")[0].rstrip("/")

    articles_to_fetch = [item.model_dump() for item in links_result.results[:args.max_articles]]
    for item in articles_to_fetch:
        if item["link"] and not item["link"].startswith("http"):
            item["link"] = urljoin(base_url + "/", item["link"].lstrip("/"))
    print(f"\n  Found {len(links_result.results)} links, processing {len(articles_to_fetch)}")

    # STEP 2: Fetch and extract each article
    print("\n" + "=" * 60)
    print("STEP 2: Extracting articles")
    print("=" * 60)

    extracted_articles = []

    for i, item in enumerate(articles_to_fetch, 1):
        article_url = item.get("link", "")
        article_title = item.get("title", "N/A")

        print(f"\n--- Article {i}/{len(articles_to_fetch)}: {article_title[:60]}... ---")
        print(f"  URL: {article_url}")

        step2_start = time.time()

        try:
            article_html = fetch_html(article_url)
            print(f"  Downloaded: {len(article_html)} chars")

            article_result = extract_article(article_html, structured_article_llm)
            article_data = article_result.model_dump()
            article_data["url"] = article_url
            article_data["listing_title"] = article_title

            step2_duration = time.time() - step2_start
            record_timing("step2_article_extraction", step2_duration, i)
            print(f"  [step2_article_extraction] {step2_duration:.3f}s")

            extracted_articles.append(article_data)

            print(f"  Title: {article_data.get('title', 'N/A')}")
            print(f"  Date: {article_data.get('publication_date', 'N/A')}")
            print(f"  Text: {str(article_data.get('text', ''))[:100]}...")

        except Exception as e:
            step2_duration = time.time() - step2_start
            record_timing("step2_article_extraction", step2_duration, i)
            print(f"  [step2_article_extraction] {step2_duration:.3f}s (ERROR)")
            print(f"  Error: {e}")
            continue

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_articles, f, ensure_ascii=False, indent=2)

    total_duration = time.time() - total_start
    record_timing("total_scrape", total_duration)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Links found: {len(links_result.results)}")
    print(f"  Articles extracted: {len(extracted_articles)}")
    print(f"  Total time: {total_duration:.3f}s")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
