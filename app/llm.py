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
            model_kwargs={"device_map": "auto", "use_cache": False},
            pipeline_kwargs={"do_sample": False, "max_new_tokens": 1024, "return_full_text": False},
        )
        tokenizer = llm.pipeline.tokenizer
        if not getattr(tokenizer, "chat_template", None):
            tokenizer.chat_template = (
                "{% for message in messages %}"
                "{% if message['role'] == 'user' %}"
                "{{ '<|start_header_id|>user<|end_header_id|>\n\n' + message['content'] + '<|eot_id|>' }}"
                "{% elif message['role'] == 'assistant' %}"
                "{{ '<|start_header_id|>assistant<|end_header_id|>\n\n' + message['content'] + '<|eot_id|>' }}"
                "{% endif %}"
                "{% endfor %}"
                "{{ '<|start_header_id|>assistant<|end_header_id|>\n\n' }}"
            )
        return ChatHuggingFace(llm=llm)

    else:
        raise ValueError(f"Unknown provider: {provider}")


def _unwrap_type(field_type):
    args = getattr(field_type, "__args__", None)
    if args:
        for arg in args:
            if arg is not type(None):
                return arg
    return field_type


def _parse_output(text: str, schema: Type[BaseModel]) -> BaseModel:
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Ecco") or line.startswith("---"):
            continue
        line = re.sub(r"^\*\s+", "", line)
        line = line.replace("**", "")
        sep = "=" if "=" in line else ":" if ":" in line else None
        if sep is None:
            continue
        key, _, value = line.partition(sep)
        key = key.strip().strip("*").strip()
        value = value.strip()

        if key not in schema.model_fields:
            continue

        field_info = schema.model_fields[key]
        field_type = field_info.annotation

        if value in ("None", "null", ""):
            args = getattr(field_type, "__args__", None)
            if args and type(None) in args:
                result[key] = None
            continue

        value = value.strip('"').strip("'")

        origin = getattr(field_type, "__origin__", None)
        if origin is type(None):
            result[key] = None
            continue

        inner_type = _unwrap_type(field_type)

        if hasattr(inner_type, "model_fields"):
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
            result[key] = inner_type(**inner)
        elif inner_type is bool:
            result[key] = value.lower() in ("true", "1", "yes")
        elif inner_type is int:
            try:
                result[key] = int(value)
            except ValueError:
                result[key] = None
        elif inner_type is float:
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

    from langchain_core.messages import HumanMessage

    class _StructuredWrapper:
        def invoke(self, prompt):
            if isinstance(prompt, str):
                prompt = [HumanMessage(content=prompt)]
            response = llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            print("--- RAW MODEL OUTPUT ---")
            print(text[:500])
            print("--- END RAW ---")
            return _parse_output(text, schema)

    return _StructuredWrapper()


detection_llm = _make_llm(_load_config()["llm"]["detection_model"])
extraction_llm = _make_llm(_load_config()["llm"]["extraction_model"])