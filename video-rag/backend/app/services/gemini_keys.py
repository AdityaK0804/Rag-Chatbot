import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeminiKey:
    index: int | None
    key: str
    label: str


def load_gemini_keys() -> list[GeminiKey]:
    load_dotenv(override=True)
    keys: list[GeminiKey] = []

    for i in range(1, 4):
        value = os.getenv(f"GEMINI_API_KEY_{i}")
        if value:
            keys.append(GeminiKey(index=i, key=value, label=str(i)))

    if not keys:
        legacy = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if legacy:
            keys.append(GeminiKey(index=None, key=legacy, label="legacy"))

    return keys


def log_key_usage(key: GeminiKey, total: int, context: str) -> None:
    if key.index is not None:
        logger.info("Gemini %s using key %d/%d", context, key.index, total)
    else:
        logger.info("Gemini %s using legacy key", context)
