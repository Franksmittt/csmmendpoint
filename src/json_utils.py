"""Parse JSON from CrewAI outputs (handles optional markdown fences)."""

import json
import re


def strip_markdown_fences(text: str) -> str:
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def parse_crew_json(raw: str | None) -> dict:
    if raw is None or not str(raw).strip():
        raise ValueError("Crew output is empty")
    cleaned = strip_markdown_fences(str(raw))
    return json.loads(cleaned)
