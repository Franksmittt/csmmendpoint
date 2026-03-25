"""Soft signals from Posted posts with engagement metrics — crew injection + dashboard."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import database as db

MIN_POSTS_FOR_INJECTION = 3


def _eligible_posts(client_id: int) -> list[dict[str, Any]]:
    """Posted rows with at least one non-zero engagement metric (likes or reach)."""
    posts = db.get_posts_for_client(client_id)
    out: list[dict[str, Any]] = []
    for p in posts:
        if (p.get("workflow_status") or "").strip() != "Posted":
            continue
        lk_raw = p.get("engagement_likes")
        rr_raw = p.get("engagement_reach")
        if lk_raw is None or rr_raw is None:
            continue
        li = int(lk_raw)
        ri = int(rr_raw)
        if li == 0 and ri == 0:
            continue
        out.append(p)
    return out


def client_has_sufficient_engagement_data(client_id: int) -> bool:
    return len(_eligible_posts(client_id)) >= MIN_POSTS_FOR_INJECTION


def build_performance_summary(
    client_id: int,
    limit: int = 15,
    *,
    focus_pillar: str | None = None,
    focus_creative_hook: str | None = None,
) -> dict[str, Any]:
    """
    Aggregate Posted + engagement metrics into pillars, hooks, patterns, and top posts.

    With ``focus_pillar`` / ``focus_creative_hook``, prefers that slice when it has enough rows;
    otherwise falls back to account-wide eligible posts (``scope_note`` explains).
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    eligible = _eligible_posts(client_id)
    scope_note = ""

    posts = eligible
    fp = (focus_pillar or "").strip()
    fh = (focus_creative_hook or "").strip()
    if fp or fh:
        filt = [
            p
            for p in eligible
            if (not fp or (p.get("content_pillar") or "").strip() == fp)
            and (not fh or (p.get("creative_hook") or "").strip() == fh)
        ]
        if len(filt) >= MIN_POSTS_FOR_INJECTION:
            posts = filt
            scope_note = (
                f"Filtered to pillar “{fp or 'any'}” and hook “{fh or 'any'}” "
                f"({len(posts)} posts)."
            )
        elif len(eligible) >= MIN_POSTS_FOR_INJECTION:
            posts = eligible
            scope_note = (
                "Few Posted posts match this pillar/hook — showing account-wide "
                "Posted metrics instead."
            )
        else:
            posts = filt

    empty = {
        "top_pillars_by_reach": [],
        "top_hooks_by_engagement": [],
        "winning_patterns": [
            "Not enough Posted posts with reach or likes recorded yet. "
            "When at least three Posted rows include metrics, we surface patterns here "
            "and optionally feed the research agent.",
        ],
        "recent_high_performers": [],
        "insufficient_data_message": (
            "Mark posts as Posted and enter likes/reach on three or more to unlock learning."
        ),
        "computed_at": now,
        "scope_note": scope_note,
    }

    if len(posts) < MIN_POSTS_FOR_INJECTION:
        return empty

    # --- Pillars: total reach + post count ---
    pillar_reach: dict[str, int] = defaultdict(int)
    pillar_counts: dict[str, int] = defaultdict(int)
    for p in posts:
        pl = (p.get("content_pillar") or "—").strip() or "—"
        pillar_reach[pl] += int(p.get("engagement_reach") or 0)
        pillar_counts[pl] += 1

    top_pillars_by_reach = [
        {"pillar": pl, "total_reach": pillar_reach[pl], "post_count": pillar_counts[pl]}
        for pl, _ in sorted(pillar_reach.items(), key=lambda x: -x[1])[:6]
    ]

    # --- Hooks: average like-rate where reach > 0 ---
    hook_rates: dict[str, list[float]] = defaultdict(list)
    for p in posts:
        rr = int(p.get("engagement_reach") or 0)
        if rr <= 0:
            continue
        lk = int(p.get("engagement_likes") or 0)
        hk = (p.get("creative_hook") or "").strip() or "(no hook label)"
        hook_rates[hk].append(lk / rr)

    hook_rows = []
    for hk, rates in hook_rates.items():
        if not rates:
            continue
        avg = sum(rates) / len(rates)
        hook_rows.append(
            {
                "hook": hk[:120],
                "avg_like_rate": round(avg, 5),
                "post_count": len(rates),
            }
        )
    hook_rows.sort(key=lambda x: -x["avg_like_rate"])
    top_hooks_by_engagement = hook_rows[:6]

    # --- Recent high performers (by like-rate, reach > 0) ---
    scored: list[tuple[float, dict[str, Any]]] = []
    for p in posts:
        rr = int(p.get("engagement_reach") or 0)
        if rr <= 0:
            continue
        lk = int(p.get("engagement_likes") or 0)
        rate = lk / rr
        scored.append((rate, p))
    scored.sort(key=lambda x: -x[0])
    recent_high_performers: list[dict[str, Any]] = []
    for rate, p in scored[:limit]:
        cap = (p.get("caption") or "").replace("\n", " ").strip()
        recent_high_performers.append(
            {
                "caption_snippet": (cap[:140] + "…") if len(cap) > 140 else cap,
                "likes": int(p.get("engagement_likes") or 0),
                "reach": int(p.get("engagement_reach") or 0),
                "like_rate": round(rate, 5),
                "content_pillar": (p.get("content_pillar") or "—").strip() or "—",
                "creative_hook": (p.get("creative_hook") or "").strip() or "—",
            }
        )

    winning_patterns = _derive_winning_patterns(
        top_pillars_by_reach,
        top_hooks_by_engagement,
        recent_high_performers,
        posts,
    )

    return {
        "top_pillars_by_reach": top_pillars_by_reach,
        "top_hooks_by_engagement": top_hooks_by_engagement,
        "winning_patterns": winning_patterns,
        "recent_high_performers": recent_high_performers[:8],
        "insufficient_data_message": None,
        "computed_at": now,
        "scope_note": scope_note,
    }


def _derive_winning_patterns(
    top_pillars: list[dict[str, Any]],
    top_hooks: list[dict[str, Any]],
    high_perf: list[dict[str, Any]],
    posts: list[dict[str, Any]],
) -> list[str]:
    bullets: list[str] = []

    if top_pillars:
        b = top_pillars[0]
        bullets.append(
            f"• Aggregate reach is strongest under pillar “{b['pillar']}” "
            f"({b['total_reach']:,} reach, {b['post_count']} post(s)) — keep it in the mix."
        )

    if top_hooks:
        h = top_hooks[0]
        pct = h["avg_like_rate"] * 100
        if h["post_count"] >= 2:
            bullets.append(
                f"• Hook “{h['hook'][:72]}{'…' if len(h['hook']) > 72 else ''}” "
                f"averages ~{pct:.2f}% like-rate across {h['post_count']} post(s) with reach."
            )
        else:
            bullets.append(
                f"• Single standout hook “{h['hook'][:72]}” hit ~{pct:.2f}% like-rate — "
                "test similar angles when on-brief."
            )

    if high_perf:
        s = high_perf[0]
        bullets.append(
            f"• Best recent like-rate: {s['like_rate'] * 100:.2f}% "
            f"({s['likes']} likes / {s['reach']} reach) — pillar “{s['content_pillar']}”, "
            f"snippet: “{s['caption_snippet'][:100]}…”"
        )

    # Pillar-level average like-rate contrast (reach > 0 only)
    pillar_rates: dict[str, list[float]] = defaultdict(list)
    for p in posts:
        rr = int(p.get("engagement_reach") or 0)
        if rr <= 0:
            continue
        pl = (p.get("content_pillar") or "—").strip() or "—"
        pillar_rates[pl].append(int(p.get("engagement_likes") or 0) / rr)
    means = {
        pl: sum(v) / len(v)
        for pl, v in pillar_rates.items()
        if len(v) >= 2
    }
    if len(means) >= 2:
        best_pl = max(means, key=means.get)
        worst_pl = min(means, key=means.get)
        if best_pl != worst_pl:
            bullets.append(
                f"• Among pillars with 2+ measured posts, “{best_pl}” leads on mean like-rate "
                f"vs “{worst_pl}” — use as a soft cue, not a hard rule."
            )

    reaches = sorted(int(p.get("engagement_reach") or 0) for p in posts)
    median_reach = reaches[len(posts) // 2]
    hi_reach = [p for p in posts if int(p.get("engagement_reach") or 0) >= median_reach]
    if len(hi_reach) >= 2:
        bullets.append(
            f"• {len(hi_reach)} post(s) sit at or above median reach ({median_reach:,}); "
            "study their hooks and pillars when planning the next batch."
        )

    _filler = (
        "• Continue logging reach and likes on Posted work — more rows sharpen these signals."
    )
    while len(bullets) < 3:
        bullets.append(_filler)

    return bullets[:6]


def format_insights_for_research_task(winning_patterns: list[str]) -> str:
    """Single prompt block for tasks.yaml {engagement_insights}."""
    lines: list[str] = []
    for ln in winning_patterns:
        s = (ln or "").strip()
        lines.append(s if s.startswith("•") else f"• {s}")
    body = "\n".join(lines)
    return (
        "Past published performance (Posted posts with engagement metrics) — "
        "soft signals only; never contradict brand_context or invent claims; "
        "prioritize strategic fit over copying:\n"
        f"{body}"
    )
