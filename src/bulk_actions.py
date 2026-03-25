"""Bulk operations on posts (keeps Streamlit app thin)."""

from __future__ import annotations

import database as db


def duplicate_posts_for_client(client_id: int, post_ids: list[int]) -> list[int]:
    """Clone each selected post; returns new post ids in stable order."""
    ids = db.filter_post_ids_for_client(client_id, post_ids)
    out: list[int] = []
    for pid in ids:
        out.append(db.duplicate_post(pid))
    return out
