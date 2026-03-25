"""Client analytics for the dashboard (pandas + Plotly; keeps app.py thin)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import database as db
import engagement_learner

_NAVY = "#1e3a5f"
_PAPER = "#f7f4ef"
_DARK_PAPER = "#1c1c1e"
_DARK_TEXT = "#d1d1d6"


def _post_dt(p: dict[str, Any]) -> datetime | None:
    return db._parse_post_datetime(p)


def build_ai_learning_summary(client_id: int) -> dict[str, Any]:
    """Live snapshot for Analytics + post Tools (Posted + engagement metrics)."""
    return engagement_learner.build_performance_summary(client_id)


def compute_client_analytics(
    client_id: int, *, dark_mode: bool = False
) -> dict[str, Any]:
    """Build metrics and Plotly figures for one client."""
    posts = db.get_posts_for_client(client_id)
    now = datetime.now(timezone.utc)
    cut90 = now - timedelta(days=90)
    cut12w = now - timedelta(weeks=12)

    total = len(posts)

    by_ap: dict[str, int] = {}
    for p in posts:
        a = (p.get("approval_stage") or db.APPROVAL_INTERNAL_DRAFT).strip()
        by_ap[a] = by_ap.get(a, 0) + 1

    by_pillar_90: dict[str, int] = {}
    by_format_90: dict[str, int] = {}
    for p in posts:
        dt = _post_dt(p)
        if dt is None or dt < cut90:
            continue
        col = (p.get("content_pillar") or "—").strip() or "—"
        by_pillar_90[col] = by_pillar_90.get(col, 0) + 1
        fmt = (p.get("post_format") or "—").strip() or "—"
        by_format_90[fmt] = by_format_90.get(fmt, 0) + 1

    rows_w: list[dict[str, Any]] = []
    for p in posts:
        dt = _post_dt(p)
        if dt is None or dt < cut12w:
            continue
        rows_w.append({"dt": dt})

    if rows_w:
        dfw = pd.DataFrame(rows_w)
        dfw["week"] = dfw["dt"].dt.to_period("W-MON").astype(str)
        wc = dfw.groupby("week").size().reset_index(name="posts").sort_values("week")
    else:
        wc = pd.DataFrame(columns=["week", "posts"])

    if len(wc) > 0:
        fig_w = px.bar(
            wc,
            x="week",
            y="posts",
            labels={"week": "Week starting (UTC)", "posts": "Posts created"},
            color_discrete_sequence=[_NAVY],
        )
    else:
        fig_w = go.Figure()

    if dark_mode:
        fig_w.update_layout(
            template="plotly_dark",
            paper_bgcolor=_DARK_PAPER,
            plot_bgcolor=_DARK_PAPER,
            font=dict(family="Georgia, serif", color=_DARK_TEXT),
            height=360,
            margin=dict(l=48, r=24, t=40, b=48),
            title=dict(
                text="Posts created per week (last 12 weeks)", font=dict(size=16)
            ),
        )
    else:
        fig_w.update_layout(
            template="plotly_white",
            paper_bgcolor=_PAPER,
            plot_bgcolor=_PAPER,
            font=dict(family="Georgia, serif", color=_NAVY),
            height=360,
            margin=dict(l=48, r=24, t=40, b=48),
            title=dict(
                text="Posts created per week (last 12 weeks)", font=dict(size=16)
            ),
        )
    if len(wc) == 0:
        fig_w.add_annotation(
            text="No posts in the last 12 weeks",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color=_DARK_TEXT if dark_mode else _NAVY, size=14),
        )

    eng_rows: list[dict[str, Any]] = []
    for p in posts:
        lk = int(p.get("engagement_likes") or 0)
        rr = int(p.get("engagement_reach") or 0)
        if lk <= 0 and rr <= 0:
            continue
        pl = (p.get("content_pillar") or "—").strip() or "—"
        fmt = (p.get("post_format") or "—").strip() or "—"
        eng_rows.append(
            {
                "post_id": int(p["id"]),
                "likes": lk,
                "reach": rr,
                "pillar": pl,
                "format": fmt,
            }
        )

    avg_rate: float | None = None
    top_hook: str | None = None
    top_pillar: str | None = None

    hooks: dict[str, int] = {}
    for p in posts:
        h = (p.get("creative_hook") or "").strip()
        if h:
            hooks[h] = hooks.get(h, 0) + 1
    if hooks:
        top_hook = max(hooks, key=hooks.get)

    rates_by_pillar: dict[str, list[float]] = {}
    for p in posts:
        rr = int(p.get("engagement_reach") or 0)
        if rr <= 0:
            continue
        lk = int(p.get("engagement_likes") or 0)
        pl = (p.get("content_pillar") or "—").strip() or "—"
        rates_by_pillar.setdefault(pl, []).append(lk / rr)
    pillar_means = {k: sum(v) / len(v) for k, v in rates_by_pillar.items() if v}
    if pillar_means:
        top_pillar = max(pillar_means, key=pillar_means.get)

    all_rates: list[float] = []
    for p in posts:
        rr = int(p.get("engagement_reach") or 0)
        if rr <= 0:
            continue
        lk = int(p.get("engagement_likes") or 0)
        all_rates.append(lk / rr)
    if all_rates:
        avg_rate = sum(all_rates) / len(all_rates)

    if eng_rows:
        dfe = pd.DataFrame(eng_rows)
        fig_s = px.scatter(
            dfe,
            x="reach",
            y="likes",
            color="pillar",
            hover_data=["post_id", "format"],
            labels={
                "reach": "Reach",
                "likes": "Likes",
                "pillar": "Pillar",
                "format": "Format",
            },
        )
    else:
        fig_s = go.Figure()

    if dark_mode:
        fig_s.update_layout(
            template="plotly_dark",
            paper_bgcolor=_DARK_PAPER,
            plot_bgcolor=_DARK_PAPER,
            font=dict(family="Georgia, serif", color=_DARK_TEXT),
            height=400,
            margin=dict(l=48, r=24, t=40, b=48),
            title=dict(
                text="Engagement (posts with likes or reach > 0)",
                font=dict(size=16),
            ),
            legend=dict(title="Pillar", font=dict(color=_DARK_TEXT)),
        )
    else:
        fig_s.update_layout(
            template="plotly_white",
            paper_bgcolor=_PAPER,
            plot_bgcolor=_PAPER,
            font=dict(family="Georgia, serif", color=_NAVY),
            height=400,
            margin=dict(l=48, r=24, t=40, b=48),
            title=dict(
                text="Engagement (posts with likes or reach > 0)",
                font=dict(size=16),
            ),
            legend=dict(title="Pillar"),
        )
    if not eng_rows:
        fig_s.add_annotation(
            text="No engagement data yet — likes/reach are zero on all posts",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color=_DARK_TEXT if dark_mode else _NAVY, size=14),
        )

    return {
        "total_posts": total,
        "by_approval": by_ap,
        "by_pillar_90d": by_pillar_90,
        "by_format_90d": by_format_90,
        "avg_engagement_rate": avg_rate,
        "top_hook": top_hook,
        "top_pillar": top_pillar,
        "fig_weekly": fig_w,
        "fig_scatter": fig_s,
    }
