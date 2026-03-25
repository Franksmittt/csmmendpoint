"""Short-form video post format helpers (9:16 video prompt field)."""

from __future__ import annotations

SHORT_VIDEO_FORMAT = "Short Video (9:16)"


def is_short_video_format(fmt: str | None) -> bool:
    return (fmt or "").strip() == SHORT_VIDEO_FORMAT
