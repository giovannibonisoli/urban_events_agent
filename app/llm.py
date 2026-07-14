import re
from pathlib import Path
from typing import Type

import yaml
from pydantic import BaseModel


_config = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open("config.yaml", encoding="utf-8") as f:
            _config = yaml.safe_load(f)
    return _config


def _make_llm(model: str):
    cfg = _load_config()["llm"]
    provider = cfg["provider"]

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, temperature=0)

    elif provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
        llm = HuggingFacePipeline.from_model_id(
            model_id=model,
            task="text-generation",
            model_kwargs={"device_map": "auto"},
            pipeline_kwargs={"temperature": 0, "max_new_tokens": 1024},
        )
        return ChatHuggingFace(llm=llm)

    else:
        raise ValueError(f"Unknown provider: {provider}")


def _parse_output(text: str, schema: Type[BaseModel]) -> BaseModel:
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if key not in schema.model_fields:
            continue

        field_info = schema.model_fields[key]
        field_type = field_info.annotation

        if value in ("None", "null", ""):
            result[key] = None
            continue

        value = value.strip('"').strip("'")

        origin = getattr(field_type, "__origin__", None)
        if origin is type(None):
            result[key] = None
            continue

        if hasattr(field_type, "model_fields"):
            inner = {}
            day_match = re.search(r"day=(\d+)", value)
            month_match = re.search(r"month=(\d+)", value)
            year_match = re.search(r"year=(\d+)", value)
            if day_match:
                inner["day"] = int(day_match.group(1))
            if month_match:
                inner["month"] = int(month_match.group(1))
            if year_match:
                inner["year"] = int(year_match.group(1))
            result[key] = field_type(**inner)
        elif field_type is bool:
            result[key] = value.lower() in ("true", "1", "yes")
        elif field_type is int:
            try:
                result[key] = int(value)
            except ValueError:
                result[key] = None
        elif field_type is float:
            try:
                result[key] = float(value)
            except ValueError:
                result[key] = None
        else:
            result[key] = value

    return schema(**result)


def structured_llm(llm, schema: Type[BaseModel]):
    provider = _load_config()["llm"]["provider"]

    if provider == "ollama":
        return llm.with_structured_output(schema)

    class _StructuredWrapper:
        def invoke(self, prompt):
            response = llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            return _parse_output(text, schema)

    return _StructuredWrapper()


detection_llm = _make_llm(_load_config()["llm"]["detection_model"])
extraction_llm = _make_llm(_load_config()["llm"]["extraction_model"])