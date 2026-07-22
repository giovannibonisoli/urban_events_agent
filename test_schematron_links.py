import json
import re
import httpx
from bs4 import BeautifulSoup, Comment
import time

from app.llm import _make_llm, _load_config


def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag in soup(['style', 'nav', 'footer', 'img', 'picture', 'figure', 'svg']):
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


def extract_links_schematron(html_content, llm):
    clean = clean_html(html_content)
    with open("clean.html", "w") as f:
        f.write(clean)

    schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "link": {"type": "string"},
                        "date": {"type": "string"}
                    },
                    "required": ["title", "link"]
                }
            }
        },
        "required": ["results"]
    }

    prompt = f"""Extract the list of news article links from this search results page.

Find all result items that represent news articles. Each result should have:
- A title (the headline text)
- A link (the URL to the article)

Schema:
{json.dumps(schema)}

HTML:
{clean}"""

    start = time.time()

    print("Invoking LLM...")
    response = llm.invoke(prompt)
    end = time.time()

    print(f"Tempo trascorso: {end - start:.2f} secondi")
    text = response.content if hasattr(response, "content") else str(response)
    print("Raw output:")
    print(text)
    return text


def main():
    cfg = _load_config()["llm"]
    provider = cfg["provider"]
    model = cfg["scraper_model"]

    print(f"Provider: {provider}")
    print(f"Model: {model}")

    llm = _make_llm(model)

    url = "https://www.modenatoday.it/search/query/furto"

    print(f"Downloading: {url}")
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    html = response.text
    print(f"Page downloaded: {len(html)} chars")

    extracted = extract_links_schematron(html, llm)

    if extracted:
        try:
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", extracted)
            if json_match:
                extracted = json_match.group(1)
            else:
                brace_match = re.search(r"\{[\s\S]*\}", extracted)
                if brace_match:
                    extracted = brace_match.group(0)

            data = json.loads(extracted)
            print("\n" + "=" * 60)
            print("LINKS FOUND")
            print("=" * 60)

            for i, result in enumerate(data.get('results', []), 1):
                print(f"{i}. {result.get('title', 'N/A')}")
                print(f"   Link: {result.get('link', 'N/A')}")
                print(f"   Date: {result.get('date', 'N/A')}")
                print()

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(extracted[:500])


if __name__ == "__main__":
    main()
