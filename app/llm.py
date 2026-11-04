import json
import re
from pathlib import Path
from typing import Type

import yaml
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ValidationError

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

  elif provider == "vllm":
    from langchain_openai import ChatOpenAI

    # vLLM espone API compatibili OpenAI (api_key fittizia necessaria per LangChain)
    return ChatOpenAI(
        model=model,
        temperature=0,
        api_key=cfg.get("api_key", "EMPTY"),
        base_url=cfg.get("base_url", "http://localhost:8000/v1"),
    )

  elif provider == "openai":
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        temperature=0,
        api_key=cfg.get("api_key"),
        base_url=cfg.get("base_url"),
    )

  elif provider == "huggingface":
    from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

    llm = HuggingFacePipeline.from_model_id(
        model_id=model,
        task="text-generation",
        model_kwargs={"device_map": "auto"},
        pipeline_kwargs={
            "do_sample": False,
            "max_new_tokens": 4096,
            "return_full_text": False,
        },
    )
    tokenizer = llm.pipeline.tokenizer
    if not getattr(tokenizer, "chat_template", None):
      tokenizer.chat_template = (
          "{% for message in messages %}"
          "{% if message['role'] == 'user' %}"
          "{{ '<|start_header_id|>user<|end_header_id|>\n\n' + message['content']"
          " + '<|eot_id|>' }}"
          "{% elif message['role'] == 'assistant' %}"
          "{{ '<|start_header_id|>assistant<|end_header_id|>\n\n' +"
          " message['content'] + '<|eot_id|>' }}"
          "{% endif %}"
          "{% endfor %}"
          "{{ '<|start_header_id|>assistant<|end_header_id|>\n\n' }}"
      )
    return ChatHuggingFace(llm=llm)

  else:
    raise ValueError(f"Unknown provider: {provider}")


def _parse_output(text: str, schema: Type[BaseModel]) -> BaseModel:
  text = text.replace("\r\n", "\n").replace("\r", "\n")

  json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
  if json_match:
    text = json_match.group(1)
  else:
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
      text = brace_match.group(0)

  text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
  text = re.sub(r"\s+", " ", text).strip()

  try:
    data = json.loads(text, strict=False)
  except json.JSONDecodeError:
    print("  [WARN] JSON parse failed, attempting field extraction...")
    data = _extract_fields_from_malformed_json(text)
    if data is None:
      print("  [WARN] Field extraction failed, returning default schema")
      return schema()

  # Deserializzazione automatica di stringhe JSON annidate (es. "events": "[{...}]")
  if isinstance(data, dict):
    for key, val in list(data.items()):
      if isinstance(val, str):
        val_str = val.strip()
        if (val_str.startswith("[") and val_str.endswith("]")) or (
            val_str.startswith("{") and val_str.endswith("}")
        ):
          try:
            data[key] = json.loads(val_str)
          except json.JSONDecodeError:
            pass

  fields = schema.model_fields
  if len(fields) == 1:
    field_name = list(fields.keys())[0]
    if field_name not in data and isinstance(data, dict):
      data = {field_name: data}

  for field_name, field_info in fields.items():
    if field_name in data and data[field_name] is None:
      annotation = field_info.annotation
      ann_str = str(annotation)
      is_optional = "None" in ann_str or "Optional" in ann_str
      if not is_optional:
        if hasattr(field_info, "default") and field_info.default is not None:
          data[field_name] = field_info.default
        elif (
            hasattr(field_info, "default_factory")
            and field_info.default_factory is not None
        ):
          data[field_name] = field_info.default_factory()
        elif "str" in ann_str.lower():
          data[field_name] = ""
        else:
          del data[field_name]

  return schema(**data)


def _extract_fields_from_malformed_json(text: str) -> dict | None:
  result = {}
  pattern = (
      r'"([^"]+)"\s*:\s*("(?:[^"\\]|\\.)*"|\[[^\]]*\]|null|\d+[\d.,]*|[a-z]+)'
  )
  matches = re.findall(pattern, text)

  for key, raw_value in matches:
    raw_value = raw_value.strip()
    if raw_value.startswith('"') and raw_value.endswith('"'):
      result[key] = raw_value[1:-1]
    elif raw_value.startswith("[") and raw_value.endswith("]"):
      try:
        items = json.loads(raw_value, strict=False)
        if isinstance(items, list):
          result[key] = items  # <-- Salva la lista nativa!
        else:
          result[key] = raw_value
      except json.JSONDecodeError:
          result[key] = raw_value
    elif raw_value == "null":
      result[key] = ""
    elif raw_value.replace(".", "", 1).replace(",", "", 1).isdigit():
      result[key] = raw_value
    else:
      result[key] = raw_value

  return result if result else None


class _RetryWrapper:
  """Wrapper universale che applica un retry loop nativo in caso di ValidationError."""

  def __init__(self, chain, schema_cls):
    self.chain = chain
    self.schema_cls = schema_cls

  def invoke(self, prompt, max_retries: int = 3):
    current_prompt = prompt if isinstance(prompt, list) else [prompt]

    for attempt in range(max_retries):
      try:
        return self.chain.invoke(current_prompt)
      except (ValidationError, Exception) as err:
        if attempt == max_retries - 1:
          print(
              f"  [ERROR] Tentativi esauriti ({max_retries}) per"
              f" {self.schema_cls.__name__}."
          )
          raise err

        print(
            f"  [RETRY {attempt + 1}/{max_retries}] Errore per"
            f" {self.schema_cls.__name__}: {err}. Riprovo..."
        )

        retry_msg = HumanMessage(
            content=(
                f"La risposta precedente non è valida ed ha causato l'errore:"
                f" {err}.\nRestituisci un JSON valido conforme allo schema"
                f" {self.schema_cls.__name__}."
            )
        )

        if isinstance(current_prompt, list):
          current_prompt.append(retry_msg)
        else:
          current_prompt = [current_prompt, retry_msg]


def structured_llm(llm, schema: Type[BaseModel]):
  provider = _load_config()["llm"]["provider"]

  # Per Ollama, OpenAI e vLLM usiamo con with_structured_output di LangChain
  if provider in ("ollama", "openai", "vllm"):
    base_chain = llm.with_structured_output(schema)
  else:
    # Per Hugging Face manteniamo il tuo wrapper custom con _parse_output
    class _StructuredWrapper:

      def invoke(self, prompt):
        if isinstance(prompt, str):
          prompt = [HumanMessage(content=prompt)]
        response = llm.invoke(prompt)
        text = (
            response.content if hasattr(response, "content") else str(response)
        )
        return _parse_output(text, schema)

    base_chain = _StructuredWrapper()

  # Avvolgiamo sia HuggingFace che vLLM nel Retry Loop universale
  return _RetryWrapper(base_chain, schema)


detection_llm = _make_llm(_load_config()["llm"]["detection_model"])
extraction_llm = _make_llm(_load_config()["llm"]["extraction_model"])
