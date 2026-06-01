import json
import hashlib
from pathlib import Path

CACHE_PATH = Path("chroma_data/.url_cache.json")


def _read() -> set:
    if CACHE_PATH.exists():
        return set(json.loads(CACHE_PATH.read_text()))
    return set()


def _write(cache: set):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(list(cache)))


def is_cached(url: str) -> bool:
    return hashlib.md5(url.encode()).hexdigest() in _read()


def mark_cached(url: str):
    cache = _read()
    cache.add(hashlib.md5(url.encode()).hexdigest())
    _write(cache)