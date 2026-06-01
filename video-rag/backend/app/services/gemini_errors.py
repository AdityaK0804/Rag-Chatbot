import asyncio
from collections.abc import Iterator

from google.api_core import exceptions as google_exceptions


QUOTA_EXCEEDED_MESSAGE = "AI quota temporarily exhausted. Please try again later."
INVALID_API_KEY_MESSAGE = "AI service configuration error."
TIMEOUT_MESSAGE = "Request timed out. Please try again."
SERVICE_UNAVAILABLE_MESSAGE = "AI service is temporarily unavailable. Please try again later."
GENERIC_AI_ERROR_MESSAGE = "Sorry, I couldn't generate a response. Please try again."


class UserFacingGeminiError(Exception):
    """Raised when a Gemini failure has already been mapped to safe user copy."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    current: BaseException | None = exc

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def is_quota_error(exc: BaseException) -> bool:
    text = " ".join(
        f"{type(chain_exc).__name__}: {chain_exc}"
        for chain_exc in iter_exception_chain(exc)
    ).lower()

    if any(isinstance(chain_exc, google_exceptions.ResourceExhausted) for chain_exc in iter_exception_chain(exc)):
        return True
    if "429" in text or "quota" in text or "resource exhausted" in text or "rate limit" in text:
        return True
    return False


def get_gemini_user_message(exc: BaseException) -> str | None:
    if isinstance(exc, UserFacingGeminiError):
        return exc.user_message

    text = " ".join(
        f"{type(chain_exc).__name__}: {chain_exc}"
        for chain_exc in iter_exception_chain(exc)
    ).lower()

    if is_quota_error(exc):
        return QUOTA_EXCEEDED_MESSAGE

    if any(
        isinstance(chain_exc, (google_exceptions.Unauthenticated, google_exceptions.PermissionDenied))
        for chain_exc in iter_exception_chain(exc)
    ):
        return INVALID_API_KEY_MESSAGE
    invalid_key_markers = (
        "api_key_invalid",
        "api key not valid",
        "invalid api key",
        "invalid api_key",
        "gemini_api_key",
        "google_api_key",
        "credentials",
        "permission denied",
        "unauthenticated",
        "401",
        "403",
    )
    if any(marker in text for marker in invalid_key_markers):
        return INVALID_API_KEY_MESSAGE

    if any(isinstance(chain_exc, google_exceptions.DeadlineExceeded) for chain_exc in iter_exception_chain(exc)):
        return TIMEOUT_MESSAGE
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return TIMEOUT_MESSAGE
    timeout_markers = (
        "deadline exceeded",
        "timed out",
        "timeout",
        "timeouterror",
        "request timed out",
    )
    if any(marker in text for marker in timeout_markers):
        return TIMEOUT_MESSAGE

    if any(isinstance(chain_exc, google_exceptions.ServiceUnavailable) for chain_exc in iter_exception_chain(exc)):
        return SERVICE_UNAVAILABLE_MESSAGE
    unavailable_markers = (
        "503",
        "service unavailable",
        "serviceunavailable",
        "temporarily unavailable",
        "connection reset",
        "failed to connect",
        "server disconnected",
        "name resolution",
    )
    if any(marker in text for marker in unavailable_markers):
        return SERVICE_UNAVAILABLE_MESSAGE

    return None
