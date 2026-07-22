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
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        text = json_match.group(1)
    else:
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            text = brace_match.group(0)

    data = json.loads(text)
    return schema(**data)


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