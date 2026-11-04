import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

from app.llm import extraction_llm, structured_llm
from app.models.date_extraction import EndDateExtraction, StartDateExtraction
from app.models.event import _DateExtraction, EventDate
from app.state import NewsArticleState


BOTH_PROMPT = Path("app/prompts/date_extractor.txt").read_text(encoding="utf-8")
START_PROMPT = Path("app/prompts/date_start_extractor.txt").read_text(encoding="utf-8")
END_PROMPT = Path("app/prompts/date_end_extractor.txt").read_text(encoding="utf-8")

# Input layouts compared by the date test. Title and subtitle are prepended to
# the article text; the event title is an extra field when requested.
VARIANTS = (
    {
        "id": "article_publication",
        "include_header": False,
        "include_event": False,
    },
    {
        "id": "article_publication_event",
        "include_header": False,
        "include_event": True,
    },
    {
        "id": "article_title_subtitle_publication",
        "include_header": True,
        "include_event": False,
    },
    {
        "id": "article_title_subtitle_publication_event",
        "include_header": True,
        "include_event": True,
    },
)


def _prompt(sys_txt: str) -> ChatPromptTemplate:
    # System text is a finished message so braces inside the prompt stay literal.
    # The article is passed as one already-built string: publication date, optional
    # event title, optional start date, and the article body.
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=sys_txt),
        ("human", "{user_input}"),
    ])


both_prompt = _prompt(BOTH_PROMPT)
start_prompt = _prompt(START_PROMPT)
end_prompt = _prompt(END_PROMPT)

structured_both = structured_llm(extraction_llm, _DateExtraction)
structured_start = structured_llm(extraction_llm, StartDateExtraction)
structured_end = structured_llm(extraction_llm, EndDateExtraction)


def _validate_date(date: EventDate | None, label: str) -> EventDate | None:
    if date is None:
        return None
    if date.day is not None and not (1 <= date.day <= 31):
        print(f"  {label}.day={date.day} invalid. Set to None.")
        date.day = None
    if date.month is not None and not (1 <= date.month <= 12):
        print(f"  {label}.month={date.month} invalid. Set to None.")
        date.month = None
    if date.year is not None and not (2000 <= date.year <= 2100):
        print(f"  {label}.year={date.year} invalid. Set to None.")
        date.year = None
    if all(v is None for v in (date.day, date.month, date.year)):
        return None
    return date


def _normalize_end_date(end_date: EventDate | None) -> EventDate | None:
    if end_date is not None and all(
        getattr(end_date, f) is None for f in ("day", "month", "year")
    ):
        return None
    return end_date


def _date_to_dict(date: EventDate | None) -> dict:
    if date is None:
        return {"day": None, "month": None, "year": None}
    return {"day": date.day, "month": date.month, "year": date.year}


def _empty_pair(error: str | None = None) -> dict:
    pair = {
        "start_date": _date_to_dict(None),
        "end_date": _date_to_dict(None),
    }
    if error:
        pair["error"] = error
    return pair


def _article_text(article: str, title: str, subtitle: str, include_header: bool) -> str:
    if not include_header:
        return article
    return f"Titolo: {title}\nSottotitolo: {subtitle}\n\n{article}"


def _user_input(
    *,
    publication_date: str,
    article: str,
    event_title: str | None,
    start_date: dict | None,
) -> str:
    parts = [f"Data di pubblicazione: {publication_date}"]
    if start_date is not None:
        parts.append(
            "Data di inizio (start_date): "
            + json.dumps(start_date, ensure_ascii=False)
        )
    if event_title is not None:
        parts.append(f"Evento da analizzare: {event_title}")
    parts.append(f"Articolo:\n\n{article}")
    return "\n\n".join(parts)


def _invoke(chain, prompt: ChatPromptTemplate, user_input: str, label: str):
    try:
        return chain.invoke(prompt.format_messages(user_input=user_input)), None
    except Exception as exc:
        print(f"  [WARN] {label} failed: {exc}")
        return None, str(exc)


def _single_request(user_input: str, label: str) -> dict:
    raw, error = _invoke(structured_both, both_prompt, user_input, label)
    if raw is None:
        return _empty_pair(error)
    start_date = _validate_date(raw.start_date, "start_date")
    end_date = _normalize_end_date(_validate_date(raw.end_date, "end_date"))
    return {
        "start_date": _date_to_dict(start_date),
        "end_date": _date_to_dict(end_date),
    }


def _separate_requests(
    *,
    publication_date: str,
    article: str,
    event_title: str | None,
    label: str,
) -> dict:
    start_input = _user_input(
        publication_date=publication_date,
        article=article,
        event_title=event_title,
        start_date=None,
    )
    start_raw, start_error = _invoke(
        structured_start,
        start_prompt,
        start_input,
        f"{label} start_date",
    )
    if start_raw is None:
        start_date = _date_to_dict(None)
    else:
        start_date = _date_to_dict(_validate_date(start_raw.start_date, "start_date"))

    end_input = _user_input(
        publication_date=publication_date,
        article=article,
        event_title=event_title,
        start_date=start_date,
    )
    end_raw, end_error = _invoke(
        structured_end,
        end_prompt,
        end_input,
        f"{label} end_date",
    )
    if end_raw is None:
        end_date = _date_to_dict(None)
    else:
        end_date = _date_to_dict(
            _normalize_end_date(_validate_date(end_raw.end_date, "end_date"))
        )

    pair = {"start_date": start_date, "end_date": end_date}
    errors = [err for err in (start_error, end_error) if err]
    if errors:
        pair["error"] = " | ".join(errors)
    return pair


def _run_variant(
    *,
    publication_date: str,
    article: str,
    event_title: str | None,
    variant_id: str,
) -> dict:
    user_input = _user_input(
        publication_date=publication_date,
        article=article,
        event_title=event_title,
        start_date=None,
    )
    single = _single_request(user_input, f"{variant_id} single_request")
    separate = _separate_requests(
        publication_date=publication_date,
        article=article,
        event_title=event_title,
        label=f"{variant_id} separate_requests",
    )
    print(f"  [{variant_id} / single_request] {single}")
    print(f"  [{variant_id} / separate_requests] {separate}")
    return {
        "single_request": single,
        "separate_requests": separate,
    }


def date_extractor(state: NewsArticleState) -> dict:
    print("\n========== DATE EXTRACTOR ==========")

    if not state["is_event"]:
        print("No event found. Skipping extraction.")
        return {}

    publication_date = state["publication_date"]
    body = state["article"]
    article_title = state.get("article_title") or ""
    article_subtitle = state.get("article_subtitle") or ""

    events = state.get("events") or []
    enriched_events = []
    # Configurations that do not use the event title are identical for every
    # event in the article, so each of those calls is made once.
    cache: dict[tuple, dict] = {}

    for ev in events:
        if not isinstance(ev, dict):
            enriched_events.append(ev)
            continue

        event_title = ev.get("title") or ""
        print(f"\nEvent: {event_title}")

        date_tests = {}
        for variant in VARIANTS:
            article = _article_text(
                body,
                article_title,
                article_subtitle,
                variant["include_header"],
            )
            title_for_prompt = event_title if variant["include_event"] else None
            cache_key = (variant["id"], title_for_prompt)
            if cache_key not in cache:
                cache[cache_key] = _run_variant(
                    publication_date=publication_date,
                    article=article,
                    event_title=title_for_prompt,
                    variant_id=variant["id"],
                )
            else:
                print(f"  [{variant['id']}] same input as a previous event, reused")
            date_tests[variant["id"]] = cache[cache_key]

        primary = date_tests["article_publication"]["single_request"]
        enriched_events.append({
            **ev,
            "start_date": primary["start_date"],
            "end_date": primary["end_date"],
            "date_tests": date_tests,
        })

    return {"events": enriched_events}
