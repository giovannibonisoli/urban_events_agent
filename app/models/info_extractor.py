from pydantic import BaseModel


class ExtractedInfo(BaseModel):
    extracted_info: dict[str, str]
