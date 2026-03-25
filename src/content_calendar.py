"""Content planning calendar helpers (pillar colors, balance math, date parsing)."""

from __future__ import annotations

import calendar as cal
import html
import io
import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

import video_prompts

# Align with dashboard editorial accents (gaps / hero); distinct per pillar.
PILLAR_HEX: dict[str, str] = {
    "Service Highlight": "#1e5f4f",
    "Did You Know? / Educational": "#5b4b8a",
    "Promotional / Sale": "#b87333",
    "Brand Authority": "#1e3a5f",
}

# Weekly mix target (posts per week per pillar) — used by “Balance this month”.
DEFAULT_WEEKLY_TARGETS: dict[str, int] = {
    "Service Highlight": 1,
    "Did You Know? / Educational": 2,
    "Promotional / Sale": 2,
    "Brand Authority": 1,
}

# Editorial PDF tokens (warm paper + navy/bronze — matches app design language)
_PDF_PAPER_RGB = (0.961, 0.941, 0.910)  # #f5f0e8
_PDF_NAVY_RGB = (30 / 255, 58 / 255, 95 / 255)  # #1e3a5f
_PDF_BRONZE_RGB = (124 / 255, 92 / 255, 54 / 255)  # #7c5c36
_PDF_BODY_RGB = (0.16, 0.16, 0.17)


def pillar_color(pillar: str) -> str:
    p = (pillar or "").strip() or "—"
    return PILLAR_HEX.get(p, "#6e6e73")


def parse_scheduled_day(raw: str | None) -> date | None:
    """Parse YYYY-MM-DD from ISO or free-text scheduled_for."""
    s = (raw or "").strip()
    if len(s) >= 10:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass
    return None


def add_months(d: date, months: int) -> date:
    m0 = d.month - 1 + months
    y = d.year + m0 // 12
    mo = m0 % 12 + 1
    last = cal.monthrange(y, mo)[1]
    day = min(d.day, last)
    return date(y, mo, day)


def month_start_end(y: int, m: int) -> tuple[date, date]:
    first = date(y, m, 1)
    last = date(y, m, cal.monthrange(y, m)[1])
    return first, last


def posts_by_scheduled_date(
    posts: Sequence[dict[str, Any]],
    range_start: date,
    range_end: date,
) -> dict[date, list[dict[str, Any]]]:
    """Bucket posts whose ``scheduled_for`` falls on a day in ``[range_start, range_end]``."""
    out: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for p in posts:
        d = parse_scheduled_day(str(p.get("scheduled_for") or ""))
        if d is None or d < range_start or d > range_end:
            continue
        out[d].append(p)
    return dict(out)


def count_pillars_in_month(
    posts: Sequence[dict[str, Any]],
    y: int,
    mo: int,
    pillars: Sequence[str],
) -> dict[str, int]:
    """Count posts with scheduled_for in that calendar month by content pillar."""
    first, last = month_start_end(y, mo)
    counts = {p: 0 for p in pillars}
    for p in posts:
        d = parse_scheduled_day(str(p.get("scheduled_for") or ""))
        if d is None or d < first or d > last:
            continue
        pl = (p.get("content_pillar") or "").strip()
        if pl in counts:
            counts[pl] += 1
    return counts


def count_scheduled_posts_in_month(
    posts: Sequence[dict[str, Any]],
    y: int,
    mo: int,
) -> int:
    """Number of posts with a ``scheduled_for`` date in the given calendar month."""
    first, last = month_start_end(y, mo)
    n = 0
    for p in posts:
        d = parse_scheduled_day(str(p.get("scheduled_for") or ""))
        if d is not None and first <= d <= last:
            n += 1
    return n


def posts_in_month_sorted(
    posts: Sequence[dict[str, Any]],
    y: int,
    mo: int,
) -> list[tuple[date, dict[str, Any]]]:
    """Scheduled posts in ``(y, mo)``, sorted by day then post id."""
    first, last = month_start_end(y, mo)
    items: list[tuple[date, dict[str, Any]]] = []
    for p in posts:
        d = parse_scheduled_day(str(p.get("scheduled_for") or ""))
        if d is None or d < first or d > last:
            continue
        items.append((d, p))
    items.sort(key=lambda x: (x[0], int(x[1].get("id") or 0)))
    return items


def approximate_weeks_in_month(y: int, mo: int) -> float:
    """Fractional weeks (Mon–Sun buckets) for scaling weekly targets."""
    first, last = month_start_end(y, mo)
    days = (last - first).days + 1
    return max(1.0, days / 7.0)


def compute_month_balance_lines(
    posts: Sequence[dict[str, Any]],
    y: int,
    mo: int,
    *,
    pillars: Sequence[str],
    weekly_targets: dict[str, int] | None = None,
) -> list[str]:
    """
    Suggest how many posts per pillar are still needed vs a weekly mix scaled to the month.

    Uses scheduled posts in the month (not created_at).
    """
    wt = weekly_targets or DEFAULT_WEEKLY_TARGETS
    weeks = approximate_weeks_in_month(y, mo)
    counts = count_pillars_in_month(posts, y, mo, pillars)
    lines: list[str] = []
    for pl in pillars:
        target = int(round(wt.get(pl, 0) * weeks))
        have = counts.get(pl, 0)
        need = max(0, target - have)
        col = pillar_color(pl)
        lines.append(
            f'<span style="color:{col};font-weight:600;">{pl}</span>: '
            f"{have} scheduled · target ~{target} · "
            f"{'✓ on track' if need == 0 else f'add ~{need} more'}"
        )
    return lines


def strip_balance_line_html(fragment: str) -> str:
    """Plain text for PDF/export from ``compute_month_balance_lines`` HTML."""
    t = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(t).strip()


def compute_month_balance_lines_plain(
    posts: Sequence[dict[str, Any]],
    y: int,
    mo: int,
    *,
    pillars: Sequence[str],
    weekly_targets: dict[str, int] | None = None,
) -> list[str]:
    """Same semantics as ``compute_month_balance_lines`` without HTML markup."""
    return [strip_balance_line_html(x) for x in compute_month_balance_lines(posts, y, mo, pillars=pillars, weekly_targets=weekly_targets)]


def _truncate(s: str, max_len: int, *, ellipsis: str = "...") -> str:
    t = (s or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max(0, max_len - len(ellipsis))] + ellipsis


def format_export_with_video_badge(post: dict[str, Any]) -> str:
    """Post format string; append video indicator when ``video_prompt`` is non-empty."""
    base = str(post.get("post_format") or "").strip()
    vp = str(post.get("video_prompt") or "").strip()
    if vp:
        return f"{base} · 🎥 Video" if base else "🎥 Video"
    return base or "—"


def format_export_badge_pdf(post: dict[str, Any]) -> str:
    """Short format label for PDF (no emoji — Helvetica lacks glyph)."""
    base = str(post.get("post_format") or "").strip()
    vp = str(post.get("video_prompt") or "").strip()
    if video_prompts.is_short_video_format(base):
        core = "Video (9:16)"
    elif "Story" in base:
        core = "9:16"
    elif "Feed" in base or "1:1" in base:
        core = "1:1"
    else:
        core = (base[:36] + "…") if len(base) > 36 else base or "—"
    if vp and not video_prompts.is_short_video_format(base):
        return f"{core} + motion brief"
    return core


def build_month_export_dataframe(
    posts: Sequence[dict[str, Any]],
    y: int,
    mo: int,
) -> pd.DataFrame:
    """Rows for CSV: one row per scheduled post in the month."""
    rows: list[dict[str, Any]] = []
    for d, p in posts_in_month_sorted(posts, y, mo):
        cap = str(p.get("caption") or "")
        vp = str(p.get("video_prompt") or "").strip()
        rows.append(
            {
                "Date": d.isoformat(),
                "Post ID": int(p.get("id") or 0),
                "Pillar": str(p.get("content_pillar") or "").strip() or "—",
                "Creative Hook": str(p.get("creative_hook") or "").strip() or "—",
                "Format": format_export_with_video_badge(p),
                "Caption": _truncate(cap, 120),
                "Video Prompt": _truncate(vp, 150) if vp else "",
                "Scheduled For": str(p.get("scheduled_for") or "").strip(),
            }
        )
    return pd.DataFrame(rows)


def safe_client_filename_fragment(name: str) -> str:
    """ASCII-ish slug for download filenames."""
    raw = re.sub(r"[^\w\s\-]", "", (name or "Client").strip(), flags=re.UNICODE)
    raw = re.sub(r"\s+", "_", raw).strip("_")
    return (raw[:60] or "Client")


def month_export_csv_bytes(
    posts: Sequence[dict[str, Any]],
    *,
    client_name: str,
    y: int,
    mo: int,
) -> tuple[bytes, str]:
    """UTF-8 CSV with BOM for Excel; returns ``(bytes, suggested_filename)``."""
    df = build_month_export_dataframe(posts, y, mo)
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    slug = safe_client_filename_fragment(client_name)
    _my = f"{cal.month_name[mo]}_{y}"
    fname = f"Endpoint_Media_{slug}_Calendar_{_my}.csv"
    return buf.getvalue(), fname


def export_month_to_pdf(
    posts: Sequence[dict[str, Any]],
    *,
    client_name: str,
    y: int,
    mo: int,
    pillars: Sequence[str],
) -> bytes:
    """
    Branded printable content plan (warm paper, navy/bronze accents).

    Uses ReportLab (bundled dependency). PDF is always light / editorial — not tied to app dark mode.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="EMTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.Color(*_PDF_NAVY_RGB),
        spaceAfter=6,
        leading=20,
    )
    sub_style = ParagraphStyle(
        name="EMSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.Color(*_PDF_BODY_RGB),
        spaceAfter=14,
        leading=14,
    )
    box_title = ParagraphStyle(
        name="EMBoxTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.Color(*_PDF_BRONZE_RGB),
        spaceAfter=6,
        leading=14,
    )
    small = ParagraphStyle(
        name="EMSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        textColor=colors.Color(0.35, 0.35, 0.37),
        leading=11,
    )
    cell_hdr = ParagraphStyle(
        name="EMCellHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=colors.white,
        leading=11,
    )
    cell_body = ParagraphStyle(
        name="EMCellBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.Color(*_PDF_BODY_RGB),
        leading=10,
    )

    flow: list[Any] = []
    flow.append(Paragraph("Endpoint Media — Content Plan", title_style))
    flow.append(
        Paragraph(
            f"<b>{html.escape(client_name)}</b> · "
            f"{html.escape(cal.month_name[mo])} {y}",
            sub_style,
        )
    )

    balance_plain = compute_month_balance_lines_plain(posts, y, mo, pillars=pillars)
    flow.append(Paragraph("Balance vs weekly targets (scaled to month)", box_title))
    bal_data = [[Paragraph(html.escape(line), small)] for line in balance_plain]
    if not bal_data:
        bal_data = [[Paragraph("(No balance data)", small)]]
    bal_tbl = Table(bal_data, colWidths=[6.5 * inch])
    bal_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*_PDF_PAPER_RGB)),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.Color(*_PDF_NAVY_RGB)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flow.append(bal_tbl)
    flow.append(Spacer(1, 0.22 * inch))

    flow.append(Paragraph("Scheduled posts", box_title))
    items = posts_in_month_sorted(posts, y, mo)
    hdr = [
        Paragraph("Date", cell_hdr),
        Paragraph("Pillar", cell_hdr),
        Paragraph("Format", cell_hdr),
        Paragraph("Hook", cell_hdr),
        Paragraph("Caption", cell_hdr),
    ]
    body_rows: list[list[Any]] = [hdr]
    for d, p in items:
        pill = str(p.get("content_pillar") or "").strip() or "—"
        ph = pillar_color(pill)
        hook = _truncate(str(p.get("creative_hook") or ""), 40)
        cap = _truncate(str(p.get("caption") or ""), 90)
        pill_para = Paragraph(
            f'<font color="{ph}">●</font> {html.escape(pill)}',
            cell_body,
        )
        body_rows.append(
            [
                Paragraph(html.escape(d.isoformat()), cell_body),
                pill_para,
                Paragraph(html.escape(format_export_badge_pdf(p)), cell_body),
                Paragraph(html.escape(hook or "—"), cell_body),
                Paragraph(html.escape(cap or "—"), cell_body),
            ]
        )

    if len(body_rows) == 1:
        body_rows.append(
            [
                Paragraph("—", cell_body),
                Paragraph("—", cell_body),
                Paragraph("—", cell_body),
                Paragraph("—", cell_body),
                Paragraph("No posts scheduled this month.", cell_body),
            ]
        )

    tw = doc.width
    col_w = [0.72 * inch, 1.35 * inch, 0.95 * inch, 1.15 * inch, tw - 0.72 - 1.35 - 0.95 - 1.15]
    sched_tbl = Table(body_rows, colWidths=col_w, repeatRows=1)
    sched_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(*_PDF_NAVY_RGB)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.Color(0.82, 0.80, 0.76)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.99, 0.98, 0.96)]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    flow.append(sched_tbl)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def _on_page(canv: Any, _doc: Any) -> None:
        canv.saveState()
        canv.setFillColorRGB(*_PDF_PAPER_RGB)
        canv.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canv.restoreState()
        canv.saveState()
        canv.setFont("Helvetica", 8)
        canv.setFillColorRGB(0.42, 0.42, 0.44)
        canv.drawString(
            0.65 * inch,
            0.45 * inch,
            f"Generated on {generated} — Endpoint Media Content Console",
        )
        canv.restoreState()

    doc.build(flow, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


def month_export_pdf_bytes(
    posts: Sequence[dict[str, Any]],
    *,
    client_name: str,
    y: int,
    mo: int,
    pillars: Sequence[str],
) -> tuple[bytes, str]:
    slug = safe_client_filename_fragment(client_name)
    _my = f"{cal.month_name[mo]}_{y}"
    fname = f"Endpoint_Media_{slug}_Calendar_{_my}.pdf"
    return export_month_to_pdf(posts, client_name=client_name, y=y, mo=mo, pillars=pillars), fname


# --- Batch generation → calendar (auto-schedule) ---------------------------------

PERIOD_NEXT_30_DAYS = "next_30_days"
PERIOD_THIS_CALENDAR_MONTH = "this_calendar_month"
PERIOD_NEXT_CALENDAR_MONTH = "next_calendar_month"


def target_period_date_range(
    period_key: str,
    *,
    anchor: date | None = None,
) -> tuple[date, date]:
    """
    Inclusive date range for scheduling presets.

    * ``next_30_days`` — today through today + 29 days.
    * ``this_calendar_month`` — rest of current month (from today through month end).
    * ``next_calendar_month`` — full next calendar month.
    """
    a = anchor or date.today()
    if period_key == PERIOD_NEXT_30_DAYS:
        return a, a + timedelta(days=29)
    if period_key == PERIOD_THIS_CALENDAR_MONTH:
        _fs, le = month_start_end(a.year, a.month)
        return max(a, _fs), le
    if period_key == PERIOD_NEXT_CALENDAR_MONTH:
        nm = add_months(date(a.year, a.month, 1), 1)
        return month_start_end(nm.year, nm.month)
    raise ValueError(f"Unknown period_key: {period_key!r}")


def balance_context_month(period_key: str, anchor: date) -> tuple[int, int]:
    """Which (year, month) to use for pillar deficit math (``pillar_sequence_balance``)."""
    if period_key == PERIOD_NEXT_CALENDAR_MONTH:
        nm = add_months(date(anchor.year, anchor.month, 1), 1)
        return nm.year, nm.month
    return anchor.year, anchor.month


def spread_schedule_dates(n: int, start: date, end: date) -> list[date]:
    """Spread ``n`` calendar days across ``[start, end]`` inclusive as evenly as possible."""
    if n <= 0:
        return []
    if end < start:
        return [start] * n
    days_span = max(1, (end - start).days + 1)
    out: list[date] = []
    for i in range(n):
        bucket = min((i * days_span) // n, days_span - 1)
        out.append(start + timedelta(days=int(bucket)))
    return out


def pillar_sequence_even(n: int, pillars: Sequence[str]) -> list[str]:
    """Round-robin pillars (same length as ``n``)."""
    pls = tuple(pillars)
    if not pls or n <= 0:
        return []
    return [pls[i % len(pls)] for i in range(n)]


def pillar_sequence_balance(
    posts: Sequence[dict[str, Any]],
    balance_year: int,
    balance_month: int,
    n: int,
    pillars: Sequence[str],
    *,
    weekly_targets: dict[str, int] | None = None,
) -> list[str]:
    """
    Order pillars for ``n`` runs to lean toward monthly targets (same logic as balance lines).

    Repeats the pillar with the largest remaining deficit each time (virtual fill-down).
    If all pillars are on track, falls back to round-robin.
    """
    wt = weekly_targets or DEFAULT_WEEKLY_TARGETS
    pls = tuple(pillars)
    if not pls or n <= 0:
        return []
    weeks = approximate_weeks_in_month(balance_year, balance_month)
    counts = count_pillars_in_month(posts, balance_year, balance_month, pls)
    deficits: dict[str, int] = {}
    for pl in pls:
        target = int(round(wt.get(pl, 0) * weeks))
        have = counts.get(pl, 0)
        deficits[pl] = max(0, target - have)
    if sum(deficits.values()) == 0:
        return pillar_sequence_even(n, pls)
    dcopy = dict(deficits)
    seq: list[str] = []
    for _ in range(n):
        pl = max(pls, key=lambda p: dcopy.get(p, 0))
        seq.append(pl)
        dcopy[pl] = max(0, dcopy.get(pl, 0) - 1)
    return seq


def auto_schedule_posts(
    client_id: int,
    post_ids: Sequence[int],
    *,
    period_key: str,
    anchor: date | None = None,
) -> tuple[date, date, list[date]]:
    """
    Set ``scheduled_for`` to noon UTC on dates spread across ``period_key``.

    Returns ``(range_start, range_end, assigned_dates)`` for UI copy.
    """
    import database as db

    start, end = target_period_date_range(period_key, anchor=anchor)
    ids = [int(x) for x in post_ids]
    dates = spread_schedule_dates(len(ids), start, end)
    for pid, d in zip(ids, dates, strict=True):
        db.update_post_scheduled_for(pid, int(client_id), noon_utc_iso(d))
    return start, end, dates


def noon_utc_iso(d: date) -> str:
    return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc).isoformat()
