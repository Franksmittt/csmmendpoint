"""SQLite persistence for clients and generated posts (manual distribution workflow)."""

from __future__ import annotations

import os
import secrets
import shutil
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _ROOT / "agency.db"

# Prevents recursive seeding when add_client() calls init_db() during apply_seed_clients().
_SEEDING_CLIENTS = False

WORKFLOW_STATUSES: tuple[str, ...] = (
    "Draft",
    "Sent to Client",
    "Posted",
)

# Admin QC before handoff to external publisher
QC_STATUS_DRAFT = "Draft"
QC_STATUS_READY = "Ready for Publisher"
QC_STATUSES: tuple[str, ...] = (QC_STATUS_DRAFT, QC_STATUS_READY)

# Publisher-side scheduling (Facebook not integrated — tracking only)
PUBLISHER_UNSCHEDULED = "Unscheduled"
PUBLISHER_SCHEDULED = "Scheduled"
PUBLISHER_POSTED = "Posted"
PUBLISHER_STATUSES: tuple[str, ...] = (
    PUBLISHER_UNSCHEDULED,
    PUBLISHER_SCHEDULED,
    PUBLISHER_POSTED,
)

# Internal approval workflow (before / alongside QC handoff)
APPROVAL_INTERNAL_DRAFT = "Internal Draft"
APPROVAL_CLIENT_REVIEW = "Client Review"
APPROVAL_APPROVED = "Approved"
APPROVAL_READY_PUBLISHER = "Ready for Publisher"
APPROVAL_STAGES: tuple[str, ...] = (
    APPROVAL_INTERNAL_DRAFT,
    APPROVAL_CLIENT_REVIEW,
    APPROVAL_APPROVED,
    APPROVAL_READY_PUBLISHER,
)

FINAL_POSTS_ROOT = _ROOT / "assets" / "final_posts"


def _conn() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _migrate_schema() -> None:
    """Add columns introduced after first deploy (safe for existing agency.db)."""
    with _conn() as conn:
        client_cols = {row[1] for row in conn.execute("PRAGMA table_info(clients)")}
        if "services_list" not in client_cols:
            conn.execute(
                "ALTER TABLE clients ADD COLUMN services_list TEXT NOT NULL DEFAULT ''"
            )
        if "target_markets" not in client_cols:
            conn.execute(
                "ALTER TABLE clients ADD COLUMN target_markets TEXT NOT NULL DEFAULT ''"
            )
        if "photography_style" not in client_cols:
            conn.execute(
                "ALTER TABLE clients ADD COLUMN photography_style TEXT NOT NULL DEFAULT ''"
            )

        post_cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
        if "workflow_status" in post_cols:
            conn.execute(
                """
                UPDATE posts SET workflow_status = 'Posted'
                WHERE workflow_status = 'Manually Posted'
                """
            )
        if "suggested_text_overlay" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN suggested_text_overlay TEXT NOT NULL DEFAULT ''"
            )
        if "content_pillar" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN content_pillar TEXT NOT NULL DEFAULT ''"
            )
        if "featured_brand" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN featured_brand TEXT NOT NULL DEFAULT ''"
            )
        if "post_format" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN post_format TEXT NOT NULL DEFAULT ''"
            )
        if "created_at" not in post_cols:
            conn.execute("ALTER TABLE posts ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
            conn.execute(
                "UPDATE posts SET created_at = generated_date WHERE created_at = '' OR created_at IS NULL"
            )
        if "image_prompt_square" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN image_prompt_square TEXT NOT NULL DEFAULT ''"
            )
        if "image_prompt_vertical" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN image_prompt_vertical TEXT NOT NULL DEFAULT ''"
            )
        # Refresh after ALTER so backfill runs on first migration pass.
        post_cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
        if "image_prompt_square" in post_cols and "image_prompt_vertical" in post_cols:
            conn.execute(
                """
                UPDATE posts
                SET image_prompt_square = image_prompt,
                    image_prompt_vertical = image_prompt
                WHERE TRIM(COALESCE(image_prompt_square, '')) = ''
                  AND TRIM(COALESCE(image_prompt, '')) != ''
                """
            )
        if "workflow_status" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN workflow_status TEXT NOT NULL DEFAULT 'Draft'"
            )
            if "publish_status" in post_cols:
                conn.execute(
                    """
                    UPDATE posts
                    SET workflow_status = 'Posted'
                    WHERE status_posted = 1 OR publish_status = 'Published'
                    """
                )
            else:
                conn.execute(
                    """
                    UPDATE posts
                    SET workflow_status = 'Posted'
                    WHERE status_posted = 1
                    """
                )
        post_cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
        if "image_square_path" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN image_square_path TEXT NOT NULL DEFAULT ''"
            )
        if "image_vertical_path" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN image_vertical_path TEXT NOT NULL DEFAULT ''"
            )
        if "qc_status" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN qc_status TEXT NOT NULL DEFAULT 'Draft'"
            )
        if "publisher_status" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN publisher_status TEXT NOT NULL DEFAULT 'Unscheduled'"
            )
        if "scheduled_for" not in post_cols:
            conn.execute("ALTER TABLE posts ADD COLUMN scheduled_for TEXT NOT NULL DEFAULT ''")
        if "approved_at" not in post_cols:
            conn.execute("ALTER TABLE posts ADD COLUMN approved_at TEXT NOT NULL DEFAULT ''")
        if "published_at" not in post_cols:
            conn.execute("ALTER TABLE posts ADD COLUMN published_at TEXT NOT NULL DEFAULT ''")
        if "publisher_notes" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN publisher_notes TEXT NOT NULL DEFAULT ''"
            )
        if "creative_hook" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN creative_hook TEXT NOT NULL DEFAULT ''"
            )
        if "approval_stage" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN approval_stage TEXT NOT NULL DEFAULT 'Internal Draft'"
            )
            conn.execute(
                """
                UPDATE posts SET approval_stage = CASE
                  WHEN TRIM(COALESCE(qc_status,'')) = 'Ready for Publisher' THEN 'Ready for Publisher'
                  ELSE 'Internal Draft'
                END
                """
            )
        if "client_review_token" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN client_review_token TEXT NOT NULL DEFAULT ''"
            )
        if "client_review_comment" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN client_review_comment TEXT NOT NULL DEFAULT ''"
            )
        if "publisher_platform" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN publisher_platform TEXT NOT NULL DEFAULT ''"
            )
        if "engagement_likes" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN engagement_likes INTEGER NOT NULL DEFAULT 0"
            )
        if "engagement_reach" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN engagement_reach INTEGER NOT NULL DEFAULT 0"
            )
        if "critic_applied" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN critic_applied INTEGER NOT NULL DEFAULT 0"
            )
        post_cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
        if "video_prompt" not in post_cols:
            conn.execute(
                "ALTER TABLE posts ADD COLUMN video_prompt TEXT NOT NULL DEFAULT ''"
            )
        conn.commit()

        # Version history table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS post_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                version_num INTEGER NOT NULL,
                caption TEXT NOT NULL,
                image_prompt_square TEXT NOT NULL DEFAULT '',
                image_prompt_vertical TEXT NOT NULL DEFAULT '',
                suggested_text_overlay TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_post_versions_post_id ON post_versions(post_id)"
        )
        conn.commit()


def _seed_default_clients_if_empty() -> None:
    """First deploy / empty DB: insert Alberton Tyre Clinic, Battery Mart, Miwesu from code."""
    global _SEEDING_CLIENTS
    if _SEEDING_CLIENTS:
        return
    try:
        with _conn() as conn:
            n = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        if int(n) > 0:
            return
    except Exception:
        return
    _SEEDING_CLIENTS = True
    try:
        from seed_clients import apply_seed_clients

        apply_seed_clients()
    finally:
        _SEEDING_CLIENTS = False


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                industry TEXT NOT NULL,
                brand_context TEXT NOT NULL,
                tone TEXT NOT NULL DEFAULT '',
                services_list TEXT NOT NULL DEFAULT '',
                target_markets TEXT NOT NULL DEFAULT '',
                photography_style TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                generated_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT '',
                caption TEXT NOT NULL,
                image_prompt TEXT NOT NULL,
                suggested_text_overlay TEXT NOT NULL DEFAULT '',
                content_pillar TEXT NOT NULL DEFAULT '',
                featured_brand TEXT NOT NULL DEFAULT '',
                post_format TEXT NOT NULL DEFAULT '',
                status_posted INTEGER NOT NULL DEFAULT 0,
                workflow_status TEXT NOT NULL DEFAULT 'Draft',
                FOREIGN KEY (client_id) REFERENCES clients (id)
            );
            """
        )
        conn.commit()
    _migrate_schema()
    _seed_default_clients_if_empty()


def add_client(
    company_name: str,
    industry: str,
    brand_context: str,
    tone: str = "",
    services_list: str = "",
    target_markets: str = "",
    photography_style: str = "",
) -> int:
    init_db()
    with _conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO clients (
                company_name, industry, brand_context, tone,
                services_list, target_markets, photography_style
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name.strip(),
                industry.strip(),
                brand_context.strip(),
                tone.strip(),
                services_list.strip(),
                target_markets.strip(),
                photography_style.strip(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_client(
    client_id: int,
    *,
    company_name: str | None = None,
    industry: str | None = None,
    brand_context: str | None = None,
    tone: str | None = None,
    services_list: str | None = None,
    target_markets: str | None = None,
    photography_style: str | None = None,
) -> None:
    """Update any provided fields; omitted fields stay unchanged."""
    init_db()
    fields: list[str] = []
    values: list[Any] = []
    if company_name is not None:
        fields.append("company_name = ?")
        values.append(company_name.strip())
    if industry is not None:
        fields.append("industry = ?")
        values.append(industry.strip())
    if brand_context is not None:
        fields.append("brand_context = ?")
        values.append(brand_context.strip())
    if tone is not None:
        fields.append("tone = ?")
        values.append(tone.strip())
    if services_list is not None:
        fields.append("services_list = ?")
        values.append(services_list.strip())
    if target_markets is not None:
        fields.append("target_markets = ?")
        values.append(target_markets.strip())
    if photography_style is not None:
        fields.append("photography_style = ?")
        values.append(photography_style.strip())
    if not fields:
        return
    values.append(client_id)
    with _conn() as conn:
        conn.execute(
            f"UPDATE clients SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()


def find_client_id_by_name_substring(substring: str) -> int | None:
    """Return first client id where company_name contains substring (case-insensitive)."""
    init_db()
    needle = substring.strip().lower()
    if not needle:
        return None
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, company_name FROM clients",
        ).fetchall()
    for row in rows:
        if needle in str(row["company_name"]).lower():
            return int(row["id"])
    return None


def get_all_clients() -> list[dict[str, Any]]:
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, company_name, industry, brand_context, tone,
                   services_list, target_markets, photography_style
            FROM clients
            ORDER BY company_name
            """
        ).fetchall()
    return [dict(r) for r in rows]


def _post_timestamp_iso(post: dict[str, Any]) -> str:
    raw = (post.get("created_at") or "").strip() or (
        post.get("generated_date") or ""
    ).strip()
    return raw


def _parse_post_datetime(post: dict[str, Any]) -> datetime | None:
    raw = _post_timestamp_iso(post)
    if not raw:
        return None
    ts = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def save_post(
    client_id: int,
    caption: str,
    image_prompt_square: str,
    image_prompt_vertical: str,
    *,
    suggested_text_overlay: str = "",
    content_pillar: str = "",
    featured_brand: str = "",
    post_format: str = "",
    workflow_status: str = "Draft",
    creative_hook: str = "",
    approval_stage: str = APPROVAL_INTERNAL_DRAFT,
    critic_applied: bool = False,
    video_prompt: str = "",
) -> int:
    """Persist caption plus two image prompts: 1:1 feed/square and 9:16 stories vertical."""
    init_db()
    sq = (image_prompt_square or "").strip()
    vert = (image_prompt_vertical or "").strip()
    vp = (video_prompt or "").strip()
    combined = (
        f"=== 1:1 (feed / square) ===\n{sq}\n\n=== 9:16 (stories / vertical) ===\n{vert}"
    )
    generated = datetime.now(timezone.utc).isoformat()
    wf = workflow_status.strip() if workflow_status.strip() in WORKFLOW_STATUSES else "Draft"
    posted = 1 if wf == "Posted" else 0
    stage = approval_stage.strip()
    if stage not in APPROVAL_STAGES:
        stage = APPROVAL_INTERNAL_DRAFT
    with _conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO posts (
                client_id, generated_date, created_at, caption, image_prompt,
                image_prompt_square, image_prompt_vertical,
                suggested_text_overlay, content_pillar, featured_brand, post_format,
                status_posted, workflow_status,
                creative_hook, approval_stage, critic_applied, video_prompt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                generated,
                generated,
                caption,
                combined,
                sq,
                vert,
                suggested_text_overlay,
                content_pillar.strip(),
                featured_brand.strip(),
                post_format.strip(),
                posted,
                wf,
                (creative_hook or "").strip(),
                stage,
                1 if critic_applied else 0,
                vp,
            ),
        )
        conn.commit()
        pid = int(cursor.lastrowid)
    append_post_version(
        pid,
        caption=caption,
        image_prompt_square=sq,
        image_prompt_vertical=vert,
        suggested_text_overlay=suggested_text_overlay,
        note="Created",
    )
    return pid


def duplicate_post(post_id: int) -> int:
    """Clone caption, prompts, overlay, pillar, brand, format, hook — new row, Draft, internal stage."""
    p = get_post_by_id(post_id)
    if not p:
        raise ValueError("post not found")
    return save_post(
        int(p["client_id"]),
        str(p.get("caption") or ""),
        str(p.get("image_prompt_square") or ""),
        str(p.get("image_prompt_vertical") or ""),
        suggested_text_overlay=str(p.get("suggested_text_overlay") or ""),
        content_pillar=str(p.get("content_pillar") or ""),
        featured_brand=str(p.get("featured_brand") or ""),
        post_format=str(p.get("post_format") or ""),
        workflow_status="Draft",
        creative_hook=str(p.get("creative_hook") or ""),
        approval_stage=APPROVAL_INTERNAL_DRAFT,
        critic_applied=bool(int(p.get("critic_applied") or 0)),
        video_prompt=str(p.get("video_prompt") or ""),
    )


def filter_post_ids_for_client(client_id: int, post_ids: list[int]) -> list[int]:
    """Deduplicate and return only post ids that belong to ``client_id`` (stable order)."""
    if not post_ids:
        return []
    uniq: list[int] = []
    seen: set[int] = set()
    for x in post_ids:
        xi = int(x)
        if xi not in seen:
            seen.add(xi)
            uniq.append(xi)
    init_db()
    placeholders = ",".join("?" * len(uniq))
    with _conn() as conn:
        rows = conn.execute(
            f"SELECT id FROM posts WHERE client_id = ? AND id IN ({placeholders})",
            (client_id, *uniq),
        ).fetchall()
    ok = {int(r["id"]) for r in rows}
    return [i for i in uniq if i in ok]


def bulk_mark_ready_for_publisher(client_id: int, post_ids: list[int]) -> int:
    """Set QC ready + approval stage for all matching posts."""
    ids = filter_post_ids_for_client(client_id, post_ids)
    if not ids:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    init_db()
    ph = ",".join("?" * len(ids))
    with _conn() as conn:
        conn.execute(
            f"""
            UPDATE posts
            SET qc_status = ?, approved_at = ?, approval_stage = ?
            WHERE client_id = ? AND id IN ({ph})
            """,
            (QC_STATUS_READY, now, APPROVAL_READY_PUBLISHER, client_id, *ids),
        )
        conn.commit()
    return len(ids)


def bulk_set_approval_stage(client_id: int, post_ids: list[int], stage: str) -> int:
    s = stage.strip()
    if s not in APPROVAL_STAGES:
        raise ValueError(f"Invalid approval stage {stage!r}")
    ids = filter_post_ids_for_client(client_id, post_ids)
    if not ids:
        return 0
    init_db()
    ph = ",".join("?" * len(ids))
    with _conn() as conn:
        conn.execute(
            f"UPDATE posts SET approval_stage = ? WHERE client_id = ? AND id IN ({ph})",
            (s, client_id, *ids),
        )
        conn.commit()
    return len(ids)


def delete_posts_for_client(client_id: int, post_ids: list[int]) -> int:
    """Remove posts (CASCADE versions) and best-effort delete ``assets/final_posts/...`` folders."""
    ids = filter_post_ids_for_client(client_id, post_ids)
    if not ids:
        return 0
    for pid in ids:
        d = FINAL_POSTS_ROOT / f"client_{client_id}" / f"post_{pid}"
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    init_db()
    ph = ",".join("?" * len(ids))
    with _conn() as conn:
        cur = conn.execute(
            f"DELETE FROM posts WHERE client_id = ? AND id IN ({ph})",
            (client_id, *ids),
        )
        conn.commit()
    return int(cur.rowcount) if cur.rowcount is not None and cur.rowcount >= 0 else len(ids)


def get_posts_for_client(client_id: int) -> list[dict[str, Any]]:
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, client_id, generated_date, created_at, caption, image_prompt,
                   image_prompt_square, image_prompt_vertical,
                   suggested_text_overlay, content_pillar, featured_brand, post_format,
                   status_posted, workflow_status,
                   image_square_path, image_vertical_path,
                   qc_status, publisher_status, scheduled_for,
                   approved_at, published_at, publisher_notes,
                   creative_hook, approval_stage, client_review_token, client_review_comment,
                   publisher_platform, engagement_likes, engagement_reach, critic_applied,
                   video_prompt
            FROM posts
            WHERE client_id = ?
            ORDER BY COALESCE(NULLIF(created_at, ''), generated_date) DESC
            """,
            (client_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def client_post_sequence_by_id(client_id: int) -> dict[int, int]:
    """Map post row id → per-client sequence number (oldest = 1) for display labels."""
    posts = get_posts_for_client(client_id)

    def sort_key(p: dict[str, Any]) -> tuple:
        dt = _parse_post_datetime(p)
        t = dt or datetime.min.replace(tzinfo=timezone.utc)
        return (t, int(p["id"]))

    asc = sorted(posts, key=sort_key)
    return {int(p["id"]): i + 1 for i, p in enumerate(asc)}


def set_post_posted(post_id: int, posted: bool = True) -> None:
    """Legacy: sync boolean posted flag + workflow."""
    init_db()
    wf = "Posted" if posted else "Draft"
    with _conn() as conn:
        conn.execute(
            """
            UPDATE posts
            SET status_posted = ?, workflow_status = ?
            WHERE id = ?
            """,
            (1 if posted else 0, wf, post_id),
        )
        conn.commit()


def update_post_scheduled_for(post_id: int, client_id: int, scheduled_for: str) -> None:
    """Set publisher ``scheduled_for`` (ISO or free text); must belong to client."""
    init_db()
    sf = (scheduled_for or "").strip()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM posts WHERE id = ? AND client_id = ?",
            (post_id, client_id),
        ).fetchone()
        if not row:
            raise ValueError("post not found for this client")
        conn.execute(
            "UPDATE posts SET scheduled_for = ? WHERE id = ?",
            (sf, post_id),
        )
        conn.commit()


def create_scheduled_placeholder_post(
    client_id: int,
    *,
    content_pillar: str,
    scheduled_for_iso: str,
    post_format: str = "Standard Feed Post (1:1 Ratio)",
) -> int:
    """Minimal draft post tied to a calendar slot; flesh out in Dashboard."""
    cap = "[Calendar placeholder — open in Dashboard to generate content]"
    pid = save_post(
        client_id,
        cap,
        "Placeholder — replace with 1:1 image prompt in Dashboard.",
        "Placeholder — replace with 9:16 image prompt in Dashboard.",
        suggested_text_overlay="{}",
        content_pillar=content_pillar,
        featured_brand="",
        post_format=post_format,
        workflow_status="Draft",
        creative_hook="",
        approval_stage=APPROVAL_INTERNAL_DRAFT,
        critic_applied=False,
    )
    update_post_scheduled_for(pid, client_id, scheduled_for_iso)
    return pid


def update_post_workflow_status(post_id: int, status: str) -> None:
    """Manual distribution lifecycle: Draft → Sent to Client → Manually Posted."""
    normalized = status.strip()
    if normalized not in WORKFLOW_STATUSES:
        raise ValueError(
            f"Invalid workflow status {status!r}; expected one of {list(WORKFLOW_STATUSES)}"
        )
    init_db()
    posted = 1 if normalized == "Posted" else 0
    with _conn() as conn:
        conn.execute(
            """
            UPDATE posts
            SET workflow_status = ?, status_posted = ?
            WHERE id = ?
            """,
            (normalized, posted, post_id),
        )
        conn.commit()


def get_content_gap_analysis(
    client_id: int,
    *,
    content_pillars: Sequence[str],
    featured_brands: Sequence[str],
    window_days: int = 30,
    stale_days: int = 14,
    brand_none_label: str = "None",
) -> list[dict[str, Any]]:
    """
    Compare recent posts to expected pillars and co-brands; return actionable gap alerts.

    Each alert: kind, message, optional pillar/brand for auto-fill, severity (info|warning).
    """
    init_db()
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)
    stale_cutoff = now - timedelta(days=stale_days)

    posts = get_posts_for_client(client_id)

    def in_window(p: dict[str, Any]) -> bool:
        dt = _parse_post_datetime(p)
        return dt is not None and dt >= window_start

    recent = [p for p in posts if in_window(p)]

    def last_match(
        *,
        pillar: str | None = None,
        brand: str | None = None,
    ) -> datetime | None:
        best: datetime | None = None
        for p in posts:
            if pillar is not None and (p.get("content_pillar") or "").strip() != pillar:
                continue
            if brand is not None and (p.get("featured_brand") or "").strip() != brand:
                continue
            dt = _parse_post_datetime(p)
            if dt is None:
                continue
            if best is None or dt > best:
                best = dt
        return best

    alerts: list[dict[str, Any]] = []

    for pillar in content_pillars:
        p = pillar.strip()
        if not p:
            continue
        last_p = last_match(pillar=p)
        had_recent = any(
            (x.get("content_pillar") or "").strip() == p for x in recent
        )
        if not had_recent:
            if last_p is None:
                alerts.append(
                    {
                        "kind": "pillar_missing",
                        "severity": "warning",
                        "message": (
                            f"⚠️ No posts tagged **{p}** in the last {window_days} days "
                            f"(no history for this pillar yet)."
                        ),
                        "pillar": p,
                        "brand": None,
                        "days": None,
                    }
                )
            else:
                days = max(0, (now - last_p).days)
                alerts.append(
                    {
                        "kind": "pillar_stale",
                        "severity": "warning",
                        "message": (
                            f"⚠️ You haven't posted about **{p}** in {days} days "
                            f"(nothing in the last {window_days}-day window)."
                        ),
                        "pillar": p,
                        "brand": None,
                        "days": days,
                    }
                )
        elif last_p is not None and last_p < stale_cutoff:
            days = (now - last_p).days
            alerts.append(
                {
                    "kind": "pillar_stale",
                    "severity": "info",
                    "message": (
                        f"💡 **{p}** last appeared {days} days ago — refresh this angle soon."
                    ),
                    "pillar": p,
                    "brand": None,
                    "days": days,
                }
            )

    for brand in featured_brands:
        b = (brand or "").strip()
        if not b or b == brand_none_label:
            continue
        last_b = last_match(brand=b)
        had_recent = any(
            (x.get("featured_brand") or "").strip() == b for x in recent
        )
        if not had_recent:
            if last_b is None:
                alerts.append(
                    {
                        "kind": "brand_missing",
                        "severity": "info",
                        "message": (
                            f"💡 Suggestion: feature **{b}** next — "
                            f"no co-branded posts in the last {window_days} days."
                        ),
                        "pillar": None,
                        "brand": b,
                        "days": None,
                    }
                )
            else:
                days = max(0, (now - last_b).days)
                alerts.append(
                    {
                        "kind": "brand_stale",
                        "severity": "info",
                        "message": (
                            f"💡 **{b}** hasn't been featured in {days} days "
                            f"(nothing in the last {window_days}-day window)."
                        ),
                        "pillar": None,
                        "brand": b,
                        "days": days,
                    }
                )
        elif last_b is not None and last_b < stale_cutoff:
            days = (now - last_b).days
            alerts.append(
                {
                    "kind": "brand_stale",
                    "severity": "info",
                    "message": (
                        f"💡 **{b}** last appeared {days} days ago — good candidate for the next hero post."
                    ),
                    "pillar": None,
                    "brand": b,
                    "days": days,
                }
            )

    return alerts


def resolve_asset_path(rel: str) -> Path:
    """Project-root relative path → absolute (empty if invalid)."""
    r = (rel or "").strip().replace("\\", "/")
    if not r or r.startswith("..") or r.startswith("/"):
        return Path()
    return (_ROOT / r).resolve()


def get_publisher_queue_client_ids() -> list[int]:
    """
    Comma-separated substrings in PUBLISHER_QUEUE_CLIENTS match company_name (case-insensitive).
    Example: alberton tyre clinic,alberton battery mart
    """
    raw = os.getenv("PUBLISHER_QUEUE_CLIENTS", "")
    if not raw.strip():
        return []
    needles = [s.strip().lower() for s in raw.split(",") if s.strip()]
    out: list[int] = []
    for c in get_all_clients():
        name = str(c.get("company_name") or "").lower()
        if any(n in name for n in needles):
            out.append(int(c["id"]))
    return sorted(set(out))


def get_post_by_id(post_id: int) -> dict[str, Any] | None:
    init_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    return dict(row) if row else None


def update_post_asset_paths(post_id: int, square_rel: str, vertical_rel: str) -> None:
    init_db()
    with _conn() as conn:
        conn.execute(
            """
            UPDATE posts
            SET image_square_path = ?, image_vertical_path = ?
            WHERE id = ?
            """,
            (square_rel.strip(), vertical_rel.strip(), post_id),
        )
        conn.commit()


def merge_post_asset_paths(
    post_id: int,
    *,
    square_rel: str | None = None,
    vertical_rel: str | None = None,
) -> None:
    """Update one or both asset paths without clearing the sibling column."""
    init_db()
    post = get_post_by_id(post_id)
    if not post:
        raise ValueError("post not found")
    sq = (
        square_rel.strip()
        if square_rel is not None
        else str(post.get("image_square_path") or "").strip()
    )
    vt = (
        vertical_rel.strip()
        if vertical_rel is not None
        else str(post.get("image_vertical_path") or "").strip()
    )
    update_post_asset_paths(post_id, sq, vt)


def save_post_final_assets(
    client_id: int,
    post_id: int,
    square_bytes: bytes,
    vertical_bytes: bytes,
    *,
    square_suffix: str = ".png",
    vertical_suffix: str = ".png",
) -> tuple[str, str]:
    """Write square + vertical files under assets/final_posts/ and store relative paths."""
    sq_suf = square_suffix if square_suffix.startswith(".") else f".{square_suffix}"
    vt_suf = vertical_suffix if vertical_suffix.startswith(".") else f".{vertical_suffix}"
    if sq_suf.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        sq_suf = ".png"
    if vt_suf.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        vt_suf = ".png"
    rel_sq = f"assets/final_posts/client_{client_id}/post_{post_id}/square{sq_suf}"
    rel_vt = f"assets/final_posts/client_{client_id}/post_{post_id}/vertical{vt_suf}"
    p_sq = _ROOT / rel_sq
    p_vt = _ROOT / rel_vt
    p_sq.parent.mkdir(parents=True, exist_ok=True)
    p_vt.parent.mkdir(parents=True, exist_ok=True)
    p_sq.write_bytes(square_bytes)
    p_vt.write_bytes(vertical_bytes)
    update_post_asset_paths(post_id, rel_sq, rel_vt)
    return rel_sq, rel_vt


def save_post_single_final_asset(
    client_id: int,
    post_id: int,
    data: bytes,
    *,
    asset: Literal["square", "vertical"],
    suffix: str = ".png",
) -> str:
    """Write one final image file and merge path into posts without clearing the other side."""
    suf = suffix if suffix.startswith(".") else f".{suffix}"
    if suf.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        suf = ".png"
    side = "square" if asset == "square" else "vertical"
    rel = f"assets/final_posts/client_{client_id}/post_{post_id}/{side}{suf}"
    p = _ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    if asset == "square":
        merge_post_asset_paths(post_id, square_rel=rel)
    else:
        merge_post_asset_paths(post_id, vertical_rel=rel)
    return rel


def set_post_qc_ready(post_id: int) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            """
            UPDATE posts
            SET qc_status = ?, approved_at = ?, approval_stage = ?
            WHERE id = ?
            """,
            (QC_STATUS_READY, now, APPROVAL_READY_PUBLISHER, post_id),
        )
        conn.commit()


def set_post_qc_draft(post_id: int) -> None:
    init_db()
    with _conn() as conn:
        conn.execute(
            """
            UPDATE posts
            SET qc_status = ?, approved_at = ''
            WHERE id = ?
            """,
            (QC_STATUS_DRAFT, post_id),
        )
        conn.commit()


def get_posts_for_publisher(client_ids: list[int]) -> list[dict[str, Any]]:
    """Posts handed off to the external publisher (QC approved)."""
    if not client_ids:
        return []
    init_db()
    placeholders = ",".join("?" * len(client_ids))
    with _conn() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*, c.company_name AS client_company_name
            FROM posts p
            JOIN clients c ON c.id = p.client_id
            WHERE p.client_id IN ({placeholders})
              AND p.qc_status = ?
            ORDER BY COALESCE(NULLIF(p.created_at, ''), p.generated_date) DESC
            """,
            (*client_ids, QC_STATUS_READY),
        ).fetchall()
    return [dict(r) for r in rows]


def append_post_version(
    post_id: int,
    *,
    caption: str,
    image_prompt_square: str = "",
    image_prompt_vertical: str = "",
    suggested_text_overlay: str = "",
    note: str = "",
) -> int:
    """Append a snapshot row; returns new post_versions.id."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    cap = (caption or "").strip()
    sq = (image_prompt_square or "").strip()
    vert = (image_prompt_vertical or "").strip()
    ov = (suggested_text_overlay or "").strip()
    with _conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version_num), 0) AS m FROM post_versions WHERE post_id = ?",
            (post_id,),
        ).fetchone()
        next_v = int(row["m"]) + 1
        cur = conn.execute(
            """
            INSERT INTO post_versions (
                post_id, version_num, caption,
                image_prompt_square, image_prompt_vertical, suggested_text_overlay,
                created_at, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (post_id, next_v, cap, sq, vert, ov, now, (note or "").strip()),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_post_versions(post_id: int) -> list[dict[str, Any]]:
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, post_id, version_num, caption,
                   image_prompt_square, image_prompt_vertical, suggested_text_overlay,
                   created_at, note
            FROM post_versions
            WHERE post_id = ?
            ORDER BY version_num ASC, id ASC
            """,
            (post_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def ensure_client_review_token(post_id: int) -> str:
    """Return existing token or create a URL-safe token for client review links."""
    init_db()
    post = get_post_by_id(post_id)
    if not post:
        raise ValueError("post not found")
    existing = (post.get("client_review_token") or "").strip()
    if existing:
        return existing
    token = secrets.token_urlsafe(24)
    with _conn() as conn:
        conn.execute(
            "UPDATE posts SET client_review_token = ? WHERE id = ?",
            (token, post_id),
        )
        conn.commit()
    return token


def get_post_by_client_review_token(token: str) -> dict[str, Any] | None:
    t = (token or "").strip()
    if not t:
        return None
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM posts WHERE client_review_token = ?",
            (t,),
        ).fetchone()
    return dict(row) if row else None


def update_post_approval_stage(post_id: int, stage: str) -> None:
    s = stage.strip()
    if s not in APPROVAL_STAGES:
        raise ValueError(f"Invalid approval stage {stage!r}")
    init_db()
    with _conn() as conn:
        conn.execute(
            "UPDATE posts SET approval_stage = ? WHERE id = ?",
            (s, post_id),
        )
        conn.commit()


def set_client_review_comment(post_id: int, comment: str) -> None:
    init_db()
    with _conn() as conn:
        conn.execute(
            "UPDATE posts SET client_review_comment = ? WHERE id = ?",
            ((comment or "").strip(), post_id),
        )
        conn.commit()


def update_post_caption_only(post_id: int, caption: str, *, note: str = "Caption update") -> None:
    """Update caption only; refreshes combined image_prompt and appends version."""
    init_db()
    post = get_post_by_id(post_id)
    if not post:
        raise ValueError("post not found")
    cap = (caption or "").strip()
    sq = (post.get("image_prompt_square") or "").strip()
    vert = (post.get("image_prompt_vertical") or "").strip()
    combined = (
        f"=== 1:1 (feed / square) ===\n{sq}\n\n=== 9:16 (stories / vertical) ===\n{vert}"
    )
    with _conn() as conn:
        conn.execute(
            """
            UPDATE posts SET caption = ?, image_prompt = ? WHERE id = ?
            """,
            (cap, combined, post_id),
        )
        conn.commit()
    append_post_version(
        post_id,
        caption=cap,
        image_prompt_square=sq,
        image_prompt_vertical=vert,
        suggested_text_overlay=(post.get("suggested_text_overlay") or ""),
        note=note,
    )


def update_post_video_prompt(post_id: int, video_prompt: str, *, note: str = "Video prompt edit") -> None:
    """Update ``video_prompt`` only (no version row — caption/prompts unchanged)."""
    init_db()
    vp = (video_prompt or "").strip()
    with _conn() as conn:
        conn.execute(
            "UPDATE posts SET video_prompt = ? WHERE id = ?",
            (vp, post_id),
        )
        conn.commit()
    _ = note  # reserved if we extend version history for video


def update_post_creative_bundle(
    post_id: int,
    *,
    caption: str,
    image_prompt_square: str,
    image_prompt_vertical: str,
    suggested_text_overlay: str,
    creative_hook: str | None = None,
    critic_applied: bool | None = None,
    note: str = "Content update",
) -> None:
    """Replace caption + prompts + overlay; append version history row."""
    init_db()
    post = get_post_by_id(post_id)
    if not post:
        raise ValueError("post not found")
    sq = (image_prompt_square or "").strip()
    vert = (image_prompt_vertical or "").strip()
    cap = (caption or "").strip()
    ov = (suggested_text_overlay or "").strip()
    combined = (
        f"=== 1:1 (feed / square) ===\n{sq}\n\n=== 9:16 (stories / vertical) ===\n{vert}"
    )
    hook = (post.get("creative_hook") or "").strip()
    if creative_hook is not None:
        hook = creative_hook.strip()
    crit = int(post.get("critic_applied") or 0)
    if critic_applied is not None:
        crit = 1 if critic_applied else 0
    with _conn() as conn:
        conn.execute(
            """
            UPDATE posts SET
              caption = ?, image_prompt = ?,
              image_prompt_square = ?, image_prompt_vertical = ?,
              suggested_text_overlay = ?, creative_hook = ?, critic_applied = ?
            WHERE id = ?
            """,
            (cap, combined, sq, vert, ov, hook, crit, post_id),
        )
        conn.commit()
    append_post_version(
        post_id,
        caption=cap,
        image_prompt_square=sq,
        image_prompt_vertical=vert,
        suggested_text_overlay=ov,
        note=note,
    )


def update_post_engagement(
    post_id: int,
    *,
    likes: int | None = None,
    reach: int | None = None,
) -> None:
    init_db()
    fields: list[str] = []
    values: list[Any] = []
    if likes is not None:
        fields.append("engagement_likes = ?")
        values.append(int(likes))
    if reach is not None:
        fields.append("engagement_reach = ?")
        values.append(int(reach))
    if not fields:
        return
    values.append(post_id)
    with _conn() as conn:
        conn.execute(
            f"UPDATE posts SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()


def update_post_publisher_fields(
    post_id: int,
    *,
    publisher_status: str | None = None,
    scheduled_for: str | None = None,
    publisher_notes: str | None = None,
    publisher_platform: str | None = None,
    set_published_now: bool = False,
    published_at_iso: str | None = None,
) -> None:
    """Update publisher tracking fields; optional stamp when marking Posted."""
    init_db()
    fields: list[str] = []
    values: list[Any] = []
    ps_norm: str | None = None
    if publisher_status is not None:
        ps_norm = publisher_status.strip()
        if ps_norm not in PUBLISHER_STATUSES:
            raise ValueError(f"Invalid publisher status {publisher_status!r}")
        fields.append("publisher_status = ?")
        values.append(ps_norm)
    if ps_norm == PUBLISHER_POSTED and set_published_now:
        ts = (published_at_iso or "").strip()
        if not ts:
            ts = datetime.now(timezone.utc).isoformat()
        fields.append("published_at = ?")
        values.append(ts)
        fields.append("workflow_status = ?")
        values.append("Posted")
        fields.append("status_posted = ?")
        values.append(1)
    if scheduled_for is not None:
        fields.append("scheduled_for = ?")
        values.append(scheduled_for.strip())
    if publisher_notes is not None:
        fields.append("publisher_notes = ?")
        values.append(publisher_notes.strip())
    if publisher_platform is not None:
        fields.append("publisher_platform = ?")
        values.append(publisher_platform.strip())
    if not fields:
        return
    values.append(post_id)
    with _conn() as conn:
        conn.execute(
            f"UPDATE posts SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()
