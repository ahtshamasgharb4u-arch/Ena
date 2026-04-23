import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class JsonParseError(Exception):
    pass


def extract_json_object(text: str) -> str:
    """
    LLMs often wrap JSON in prose or code fences. Extract the first top-level JSON object/array.
    """
    if not text:
        raise JsonParseError("Empty response")
    s = text.strip()
    # Strip markdown fences
    if "```" in s:
        parts = s.split("```")
        # heuristically pick the largest fenced block
        s = max((p.strip() for p in parts), key=len)
        if s.startswith("json"):
            s = s[4:].strip()
    # Find first { or [
    start = None
    for i, ch in enumerate(s):
        if ch in "{[":
            start = i
            break
    if start is None:
        raise JsonParseError("No JSON start found")
    s2 = s[start:]
    # Try progressively trimming to last } or ]
    end = max(s2.rfind("}"), s2.rfind("]"))
    if end == -1:
        raise JsonParseError("No JSON end found")
    return s2[: end + 1]


def parse_and_validate(model: type[T], raw_text: str) -> T:
    try:
        js = extract_json_object(raw_text)
        data = json.loads(js)
    except Exception as e:
        raise JsonParseError(str(e)) from e
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise JsonParseError(f"Schema validation failed: {e}") from e

