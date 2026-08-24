"""Text normalization shared by structured LLM response parsers."""

_JSON_PREFIX_CHARS = "\ufeff\u200b\u200c\u200d"


def strip_json_prefix(text: str) -> str:
    """Remove only provider-added invisible characters before a JSON document."""
    if not isinstance(text, str):
        return text
    return text.lstrip(_JSON_PREFIX_CHARS)


__all__ = ["strip_json_prefix"]
