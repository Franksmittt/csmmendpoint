"""Gemini / Imagen image generation helpers (optional — requires GEMINI_API_KEY)."""

from __future__ import annotations

import os
from typing import Any

from google.genai import Client, types


def _client() -> Client:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return Client(api_key=key)


def default_imagen_model() -> str:
    return (os.getenv("IMAGEN_MODEL") or "imagen-3.0-generate-002").strip()


def generate_imagen_png_bytes(
    prompt: str,
    *,
    aspect_ratio: str,
    guidance_scale: float | None = None,
    seed: int | None = None,
    model: str | None = None,
) -> bytes:
    """
    Generate one PNG (or image/jpeg if API returns that) from a text prompt.

    aspect_ratio: one of "1:1", "9:16", "16:9", "4:3", "3:4"
    guidance_scale: optional adherence strength (Imagen — higher = stricter to prompt).
    """
    p = (prompt or "").strip()
    if not p:
        raise ValueError("prompt is empty")
    ar = aspect_ratio.strip()
    if ar not in ("1:1", "9:16", "16:9", "4:3", "3:4"):
        raise ValueError(f"unsupported aspect_ratio {aspect_ratio!r}")

    m = (model or default_imagen_model()).strip()
    cfg_kwargs: dict[str, Any] = {
        "number_of_images": 1,
        "aspect_ratio": ar,
    }
    if guidance_scale is not None:
        cfg_kwargs["guidance_scale"] = float(guidance_scale)
    if seed is not None:
        cfg_kwargs["seed"] = int(seed)

    config = types.GenerateImagesConfig(**cfg_kwargs)
    client = _client()
    resp = client.models.generate_images(model=m, prompt=p, config=config)
    if not resp.generated_images:
        raise RuntimeError("Imagen returned no images (blocked or empty response)")
    img = resp.generated_images[0].image
    if img is None:
        raise RuntimeError("Imagen image payload missing")
    data = img.image_bytes
    if data:
        return data
    raise RuntimeError("Imagen returned image without inline bytes (GCS URI not supported here)")
