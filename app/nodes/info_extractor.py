from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from app.llm import extraction_llm, structured_llm
from app.models.info_extractor import ExtractedInfo
from app.state import EventState


SYSTEM_PROMPT = Path("app/prompts/info_extractor.txt").read_text(encoding="utf-8")

full_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Articolo:\n\n{article}"),
])

structured_info = structured_llm(extraction_llm, ExtractedInfo)


def info_extractor(state: EventState) -> dict:

    print("\n========== INFO EXTRACTOR ==========")

    messages = full_prompt.format_messages(article=state["article"])
    response = structured_info.invoke(messages)

    print(response)

    return {
        "extracted_info": response.extracted_info,
    }
