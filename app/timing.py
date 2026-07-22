import time
import json
from pathlib import Path
from typing import Callable, Any
from functools import wraps


TIMING_FILE = Path("logs/execution_times.json")


def _ensure_log_dir():
    TIMING_FILE.parent.mkdir(parents=True, exist_ok=True)


def record_timing(agent_name: str, duration: float, article_index: int = None):
    _ensure_log_dir()
    
    entry = {
        "agent": agent_name,
        "duration_seconds": round(duration, 3),
        "timestamp": time.time()
    }
    if article_index is not None:
        entry["article_index"] = article_index
    
    existing = []
    if TIMING_FILE.exists():
        with open(TIMING_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    
    existing.append(entry)
    
    with open(TIMING_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def timed_node(node_fn: Callable) -> Callable:
    @wraps(node_fn)
    def wrapper(state: Any, *args, **kwargs):
        agent_name = node_fn.__name__
        start = time.time()
        result = node_fn(state, *args, **kwargs)
        duration = time.time() - start
        record_timing(agent_name, duration)
        print(f"  [{agent_name}] {duration:.3f}s")
        return result
    return wrapper


def clear_timing_log():
    _ensure_log_dir()
    with open(TIMING_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
