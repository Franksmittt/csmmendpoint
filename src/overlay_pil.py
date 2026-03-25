"""Lightweight PIL overlay preview / bake (heading + footer bands)."""

from __future__ import annotations

import io
import json
from typing import Literal

from PIL import Image, ImageDraw, ImageFont


def parse_overlay_heading_footer(overlay_raw: str) -> tuple[str, str]:
    """Parse suggested_text_overlay JSON (or empty) into heading + footer strings."""
    if not (overlay_raw or "").strip():
        return "", ""
    try:
        d = json.loads(overlay_raw)
        if isinstance(d, dict):
            return str(d.get("Heading") or "").strip(), str(d.get("Footer") or "").strip()
    except json.JSONDecodeError:
        pass
    return "", ""


def _load_default_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except OSError:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size=size)
        except OSError:
            return ImageFont.load_default()


def bake_text_overlay(
    image_bytes: bytes,
    heading: str,
    footer: str,
    *,
    band_ratio: float = 0.2,
    mode: Literal["preview", "bake"] = "bake",
    output_format: Literal["PNG", "JPEG"] = "PNG",
    jpeg_quality: int = 92,
) -> bytes:
    """
    Place heading in top band and footer in bottom band (each ``band_ratio`` of height).
    Returns PNG or JPEG bytes (JPEG for smaller final delivery files).
    """
    h_txt = (heading or "").strip()
    f_txt = (footer or "").strip()
    im = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = im.size
    band = max(8, int(h * float(band_ratio)))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if mode == "preview":
        top_fill = (0, 0, 0, 120)
        bot_fill = (0, 0, 0, 120)
    else:
        top_fill = (0, 0, 0, 160)
        bot_fill = (0, 0, 0, 160)
    draw.rectangle((0, 0, w, band), fill=top_fill)
    draw.rectangle((0, h - band, w, h), fill=bot_fill)

    title_font = _load_default_font(max(14, min(32, band // 3)))
    foot_font = _load_default_font(max(12, min(26, band // 3)))

    def _fit_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_w: int) -> str:
        if not text:
            return ""
        if draw.textlength(text, font=font) <= max_w:
            return text
        ell = "…"
        while len(text) > 1 and draw.textlength(text + ell, font=font) > max_w:
            text = text[:-1]
        return text.rstrip() + ell

    margin = max(6, w // 48)
    max_text_w = w - 2 * margin
    h_line = _fit_text(h_txt, title_font, max_text_w)
    f_line = _fit_text(f_txt, foot_font, max_text_w)

    if h_line:
        draw.text((margin, margin // 2), h_line, fill=(255, 255, 255, 255), font=title_font)
    if f_line:
        tw = draw.textlength(f_line, font=foot_font)
        draw.text(
            ((w - tw) / 2, h - band + max(4, (band - foot_font.size) // 2)),
            f_line,
            fill=(255, 255, 255, 255),
            font=foot_font,
        )

    out = Image.alpha_composite(im, overlay)
    buf = io.BytesIO()
    rgb = out.convert("RGB")
    if output_format == "JPEG":
        rgb.save(buf, format="JPEG", quality=int(jpeg_quality), optimize=True)
    else:
        rgb.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
