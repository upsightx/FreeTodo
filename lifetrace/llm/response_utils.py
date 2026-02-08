"""Utilities to safely read LiteLLM/OpenAI-like response objects.

These helpers avoid direct typed attribute access on loosely-typed SDK objects,
which keeps static type checking stable across provider wrappers.
"""

from __future__ import annotations


def get_message_content(response: object) -> str:
    """Extract first choice message content from a completion response."""
    choices = getattr(response, "choices", None)
    if not choices:
        return ""

    first_choice = None
    try:
        first_choice = choices[0]
    except Exception:
        return ""

    message = getattr(first_choice, "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    return ""


def get_delta_content(chunk: object) -> str:
    """Extract first choice delta content from a stream chunk."""
    choices = getattr(chunk, "choices", None)
    if not choices:
        return ""

    first_choice = None
    try:
        first_choice = choices[0]
    except Exception:
        return ""

    delta = getattr(first_choice, "delta", None)
    content = getattr(delta, "content", None)
    if isinstance(content, str):
        return content
    return ""


def get_usage_tokens(response: object) -> tuple[int, int] | None:
    """Extract prompt/completion token usage when available."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        return prompt_tokens, completion_tokens
    return None
