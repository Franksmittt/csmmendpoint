"""
One-shot Imagen + overlay bake pipeline (keeps Streamlit app thin).

Vertical / brand rules live in prompts produced by Crew — this module only
orchestrates generation, overlay, and bytes output.
"""

from __future__ import annotations

import logging
from typing import Literal

import image_generation
import overlay_pil

logger = logging.getLogger(__name__)

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore


def guidance_config_value(guidance_slider: float) -> float | None:
    """0.0 means “API default” — omit guidance in the Imagen request."""
    if guidance_slider <= 0.0:
        return None
    return float(guidance_slider)


def _guidance_cache_token(guidance_scale: float | None) -> str:
    return "__none__" if guidance_scale is None else f"{float(guidance_scale):.6f}"


def generate_imagen_raw_pair(
    square_prompt: str,
    vertical_prompt: str,
    *,
    guidance_scale: float | None,
    seed: int | None = None,
) -> tuple[bytes, bytes]:
    """Generate two raw images (PNG bytes from Imagen). Not cached — use ``generate_imagen_cached`` from UI."""
    return _generate_imagen_raw_pair_uncached(
        square_prompt,
        vertical_prompt,
        guidance_scale=guidance_scale,
        seed=seed,
    )


def _generate_imagen_raw_pair_uncached(
    square_prompt: str,
    vertical_prompt: str,
    *,
    guidance_scale: float | None,
    seed: int | None = None,
) -> tuple[bytes, bytes]:
    sq = (square_prompt or "").strip()
    vt = (vertical_prompt or "").strip()
    if not sq or not vt:
        raise ValueError("square and vertical prompts are required")
    logger.info("Imagen: generating 1:1 and 9:16 (guidance=%s, seed=%s)", guidance_scale, seed)
    b1 = image_generation.generate_imagen_png_bytes(
        sq,
        aspect_ratio="1:1",
        guidance_scale=guidance_scale,
        seed=seed,
    )
    b2 = image_generation.generate_imagen_png_bytes(
        vt,
        aspect_ratio="9:16",
        guidance_scale=guidance_scale,
        seed=seed,
    )
    return b1, b2


if st is not None:

    @st.cache_data(ttl=3600, show_spinner=False)
    def _generate_imagen_cached_impl(
        client_id: int,
        post_id: int,
        square_prompt: str,
        vertical_prompt: str,
        guidance_token: str,
        seed_key: int,
    ) -> tuple[bytes, bytes]:
        gs = None if guidance_token == "__none__" else float(guidance_token)
        seed = None if seed_key < 0 else int(seed_key)
        _ = client_id, post_id
        return _generate_imagen_raw_pair_uncached(
            square_prompt,
            vertical_prompt,
            guidance_scale=gs,
            seed=seed,
        )

else:  # pragma: no cover

    def _generate_imagen_cached_impl(
        client_id: int,
        post_id: int,
        square_prompt: str,
        vertical_prompt: str,
        guidance_token: str,
        seed_key: int,
    ) -> tuple[bytes, bytes]:
        gs = None if guidance_token == "__none__" else float(guidance_token)
        seed = None if seed_key < 0 else int(seed_key)
        _ = client_id, post_id
        return _generate_imagen_raw_pair_uncached(
            square_prompt,
            vertical_prompt,
            guidance_scale=gs,
            seed=seed,
        )


def generate_imagen_cached(
    client_id: int,
    post_id: int,
    square_prompt: str,
    vertical_prompt: str,
    guidance_scale: float | None,
    seed: int | None,
) -> tuple[bytes, bytes]:
    """
    Cached Imagen pair for identical (client, post, prompts, guidance, seed).

    Prompts and guidance participate in the Streamlit cache key.
    """
    return _generate_imagen_cached_impl(
        client_id,
        post_id,
        square_prompt,
        vertical_prompt,
        _guidance_cache_token(guidance_scale),
        -1 if seed is None else int(seed),
    )


def bake_overlay_pair(
    raw_square_png: bytes,
    raw_vertical_png: bytes,
    heading: str,
    footer: str,
    *,
    mode: Literal["preview", "bake"],
    output_format: Literal["PNG", "JPEG"] = "JPEG",
    jpeg_quality: int = 92,
) -> tuple[bytes, bytes]:
    """Apply heading/footer bands to both images; finals default to JPEG."""
    h = (heading or "").strip()
    f = (footer or "").strip()
    if not h and not f:
        logger.warning("Overlay bake: empty heading and footer — saving without text bands")
    fmt: Literal["PNG", "JPEG"] = "PNG" if mode == "preview" else output_format
    out_sq = overlay_pil.bake_text_overlay(
        raw_square_png,
        h,
        f,
        mode=mode,
        output_format=fmt,
        jpeg_quality=jpeg_quality,
    )
    out_vt = overlay_pil.bake_text_overlay(
        raw_vertical_png,
        h,
        f,
        mode=mode,
        output_format=fmt,
        jpeg_quality=jpeg_quality,
    )
    return out_sq, out_vt


def run_preview_then_bake(
    raw_square_png: bytes,
    raw_vertical_png: bytes,
    heading: str,
    footer: str,
) -> tuple[bytes, bytes]:
    """Preview overlay (lighter bands) for both — PNG output."""
    return bake_overlay_pair(
        raw_square_png,
        raw_vertical_png,
        heading,
        footer,
        mode="preview",
        output_format="PNG",
    )


def run_full_bake_jpeg(
    raw_square_png: bytes,
    raw_vertical_png: bytes,
    heading: str,
    footer: str,
    *,
    jpeg_quality: int = 92,
) -> tuple[bytes, bytes]:
    """Final bake for delivery — JPEG."""
    return bake_overlay_pair(
        raw_square_png,
        raw_vertical_png,
        heading,
        footer,
        mode="bake",
        output_format="JPEG",
        jpeg_quality=jpeg_quality,
    )
