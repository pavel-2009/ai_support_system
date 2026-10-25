"""Retry classification for errors returned by the OpenAI-compatible API."""

from openai import APIConnectionError, APIStatusError


def is_retryable_llm_api_error(error: BaseException) -> bool:
    """Return whether an LLM API error is likely to succeed on a later attempt."""
    if isinstance(error, APIConnectionError):
        return True

    if isinstance(error, APIStatusError):
        return error.status_code in {408, 409, 429} or error.status_code >= 500

    return False
