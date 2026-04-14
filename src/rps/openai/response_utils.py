"""Response helpers for extracting metadata."""

from __future__ import annotations

from rps.openai.litellm_runtime import LiteLLMResponse


def _item_type(item: object) -> str | None:
    """Return the type field for a response output item."""
    if isinstance(item, dict):
        return item.get("type")
    return getattr(item, "type", None)


def _item_field(item: object, name: str) -> object | None:
    """Safely read a field from a response output item."""
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def extract_reasoning_summaries(response: LiteLLMResponse) -> list[str]:
    """Return any reasoning summaries from a response output."""
    summaries: list[str] = []
    for item in getattr(response, "output", []) or []:
        if _item_type(item) != "reasoning":
            continue
        summary = _item_field(item, "summary")
        if summary is None:
            continue
        if isinstance(summary, str):
            summaries.append(summary)
        else:
            summaries.append(str(summary))
    return summaries


def extract_file_search_results(response: LiteLLMResponse) -> list[dict[str, object]]:
    """Return any file_search results from a response output."""
    items: list[dict[str, object]] = []
    for item in getattr(response, "output", []) or []:
        if _item_type(item) not in ("file_search", "file_search_call"):
            continue
        results = _item_field(item, "results") or []
        if not isinstance(results, list) or not results:
            continue
        for result in results:
            items.append(
                {
                    "filename": _item_field(result, "filename"),
                    "score": _item_field(result, "score"),
                    "attributes": _item_field(result, "attributes") or {},
                }
            )
    return items


def extract_text_output(response: LiteLLMResponse) -> str:
    """Return any assistant text content from a response output."""
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        if _item_type(item) != "message":
            continue
        content = _item_field(item, "content")
        if not content:
            continue
        if isinstance(content, str):
            chunks.append(content)
            continue
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict):
                if part.get("type") in ("output_text", "text"):
                    text = part.get("text")
                    if text:
                        chunks.append(str(text))
            else:
                chunks.append(str(part))
    return "\n".join(chunks).strip()
