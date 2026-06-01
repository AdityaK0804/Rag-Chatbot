import logging
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.services.gemini_errors import (
    INVALID_API_KEY_MESSAGE,
    QUOTA_EXCEEDED_MESSAGE,
    UserFacingGeminiError,
    is_quota_error,
)
from app.services.gemini_keys import load_gemini_keys, log_key_usage

# Ensure env vars are loaded even if this module is imported directly
load_dotenv()

logger = logging.getLogger(__name__)

# Module-level singleton — one instance for the process lifetime.
# Recreating it per request adds latency and burns unnecessary connections.
_embedder: GoogleGenerativeAIEmbeddings | None = None
_embedder_key: str | None = None


def _build_embedder(api_key: str) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=api_key,
    )


def get_embedder(api_key: str | None = None) -> GoogleGenerativeAIEmbeddings:
    global _embedder
    global _embedder_key
    if api_key is None:
        keys = load_gemini_keys()
        if not keys:
            raise UserFacingGeminiError(INVALID_API_KEY_MESSAGE)
        api_key = keys[0].key

    if _embedder is None or _embedder_key != api_key:
        _embedder = _build_embedder(api_key)
        _embedder_key = api_key
    return _embedder


async def embed_documents_with_rotation(chunks: list[str]) -> list[list[float]]:
    keys = load_gemini_keys()
    if not keys:
        raise UserFacingGeminiError(INVALID_API_KEY_MESSAGE)

    last_quota_error: BaseException | None = None
    for key in keys:
        log_key_usage(key, len(keys), "embed")
        try:
            embedder = get_embedder(api_key=key.key)
            return await embedder.aembed_documents(chunks)
        except Exception as exc:
            if is_quota_error(exc):
                last_quota_error = exc
                logger.warning("Gemini embedding quota hit with key %s; rotating.", key.label)
                continue
            raise

    if last_quota_error:
        raise UserFacingGeminiError(QUOTA_EXCEEDED_MESSAGE) from last_quota_error
    raise UserFacingGeminiError(INVALID_API_KEY_MESSAGE)
