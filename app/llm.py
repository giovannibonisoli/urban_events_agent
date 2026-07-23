import json
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
            pipeline_kwargs={"do_sample": False, "max_new_tokens": 4096, "return_full_text": False},
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

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=0,
            api_key=cfg.get("api_key"),
            base_url=cfg.get("base_url"),
        )

    else:
        raise ValueError(f"Unknown provider: {provider}")


def _parse_output(text: str, schema: Type[BaseModel]) -> BaseModel:
    # Aggressively clean the raw text first
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Find JSON block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        text = json_match.group(1)
    else:
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            text = brace_match.group(0)

    # Replace ALL newlines/tabs with spaces (inside strings too)
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Try to parse JSON, with fallback for malformed output
    try:
        data = json.loads(text, strict=False)
    except json.JSONDecodeError:
        print(f"  [WARN] JSON parse failed, attempting field extraction...")
        data = _extract_fields_from_malformed_json(text)
        if data is None:
            print(f"  [WARN] Field extraction failed, returning default schema")
            return schema()

    def _coerce_dict_values(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, list):
                    obj[key] = ", ".join(str(v) for v in value)
                elif isinstance(value, dict):
                    _coerce_dict_values(value)
                elif value is None:
                    obj[key] = ""
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = _coerce_dict_values(item)
        return obj

    fields = schema.model_fields

    # Handle case where LLM returns flat dict instead of wrapped in a key
    if len(fields) == 1:
        field_name = list(fields.keys())[0]
        field_info = fields[field_name]
        if field_name not in data and isinstance(data, dict):
            data = {field_name: data}

        # If the wrapped field is a dict[str, str], coerce all its values
        if isinstance(data.get(field_name), dict):
            annotation = field_info.annotation
            ann_str = str(annotation)
            if 'dict' in ann_str.lower() or 'Dict' in ann_str:
                _coerce_dict_values(data[field_name])

    # Remove None values for fields that have default_factory and don't accept None
    for field_name, field_info in fields.items():
        if field_name in data and data[field_name] is None:
            annotation = field_info.annotation
            ann_str = str(annotation)
            is_optional = 'None' in ann_str or 'Optional' in ann_str
            if not is_optional:
                if hasattr(field_info, 'default') and field_info.default is not None:
                    data[field_name] = field_info.default
                elif hasattr(field_info, 'default_factory') and field_info.default_factory is not None:
                    data[field_name] = field_info.default_factory()
                elif 'str' in ann_str.lower():
                    data[field_name] = ""
                else:
                    del data[field_name]

    return schema(**data)


def _extract_fields_from_malformed_json(text: str) -> dict | None:
    """Extract key-value pairs from malformed JSON using regex."""
    result = {}

    # Pattern: "key": "value" or "key": number or "key": null or "key": ["list"]
    pattern = r'"([^"]+)"\s*:\s*("(?:[^"\\]|\\.)*"|\[[^\]]*\]|null|\d+[\d.,]*|[a-z]+)'
    matches = re.findall(pattern, text)

    for key, raw_value in matches:
        raw_value = raw_value.strip()
        if raw_value.startswith('"') and raw_value.endswith('"'):
            result[key] = raw_value[1:-1]
        elif raw_value.startswith('[') and raw_value.endswith(']'):
            # Parse list and join as comma-separated string
            try:
                items = json.loads(raw_value, strict=False)
                if isinstance(items, list):
                    result[key] = ", ".join(str(v) for v in items)
                else:
                    result[key] = raw_value
            except json.JSONDecodeError:
                result[key] = raw_value
        elif raw_value == 'null':
            result[key] = ""
        elif raw_value.replace('.', '', 1).replace(',', '', 1).isdigit():
            result[key] = raw_value
        else:
            result[key] = raw_value

    return result if result else None


def structured_llm(llm, schema: Type[BaseModel]):
    provider = _load_config()["llm"]["provider"]

    if provider in ("ollama", "openai"):
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