"""Parse JSON objects out of LLM completions (strict or fenced)."""

from __future__ import annotations

import json
import re
from typing import Any

_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_payload(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = _OBJECT.search(raw)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM JSON payload must be an object")
    return data
