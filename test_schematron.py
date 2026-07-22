import json
import httpx
from bs4 import BeautifulSoup, Comment
import re

from app.llm import _make_llm, _load_config


def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'img', 'picture', 'figure', 'svg']):
        tag.decompose()

    for tag in soup.find_all(class_=['image', 'gallery', 'slider', 'carousel', 'media']):
        tag.decompose()

    text = soup.get_text(separator=' ')

    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\r+', ' ', text)
    text = re.sub(r'\t+', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r' +\.', '.', text)
    text = re.sub(r' +,', ',', text)
    text = re.sub(r' +:', ':', text)
    text = re.sub(r' +;', ';', text)

    return text.strip()


def fetch_html(url):
    print(f"Downloading: {url}")
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def extract_with_schematron(html_content, llm):
    clean = clean_html(html_content)
    print(f"Clean HTML: {len(clean)} chars")

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "text": {"type": "string"},
            "publication date": {"type": "string"}
        },
        "required": ["title", "text", "publication date"]
    }

    prompt = f"""Extract data from the HTML below into JSON matching this schema.

Schema:
{json.dumps(schema)}

HTML:
{clean}"""

    print("Invoking LLM...")
    response = llm.invoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)
    print("Raw output:")
    print(text[:500])
    return text


def main():
    cfg = _load_config()["llm"]
    provider = cfg["provider"]
    model = cfg["scraper_model"]

    print(f"Provider: {provider}")
    print(f"Model: {model}")

    llm = _make_llm(model)

    url = "https://www.gazzettadimodena.it/modena/cronaca/2026/07/22/news/con-un-martello-da-muratore-tenta-il-furto-al-supermercato-1.100897750"

    html = fetch_html(url)
    print(f"Page downloaded: {len(html)} chars")

    extracted = extract_with_schematron(html, llm)

    if extracted:
        print("\n" + "=" * 60)
        print("EXTRACTION RESULTS")
        print("=" * 60)

        try:
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", extracted)
            if json_match:
                extracted = json_match.group(1)
            else:
                brace_match = re.search(r"\{[\s\S]*\}", extracted)
                if brace_match:
                    extracted = brace_match.group(0)

            data = json.loads(extracted)
            print(f"Title: {data.get('title', 'N/A')}")
            print(f"Date: {data.get('publication date', 'N/A')}")
            print(f"Text: {data.get('text', 'N/A')[:200]}...")

            with open("articolo_estratto.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("\nSaved to 'articolo_estratto.json'")

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Raw: {extracted[:500]}...")


if __name__ == "__main__":
    main()
