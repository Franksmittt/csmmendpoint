"""
Upsert Absolute Offroad into agency.db with approved SA-focused brief.

Usage (repo root):
    uv run python scripts/upsert_absolute_offroad.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import database as db  # noqa: E402

COMPANY_NAME = "Absolute Offroad"
MATCH_SUBSTRING = "absolute offroad"

INDUSTRY = "4x4 accessories and fitment specialist — South African market (Alberton)."

BRAND_CONTEXT = """Absolute Offroad is a South African 4x4 specialist focused on technical fitment and real-world overlanding upgrades.
Location: 28 St Columb Rd, New Redruth, Alberton, 1449.
Phone / WhatsApp: +27 79 507 0901.
Email: info@absoluteoffroad.co.za.
Website: https://absoluteoffroad.co.za/
Hours: Monday-Friday 08:00-17:00.

Core positioning: engineering-first fitment quality for suspension, protection, recovery, and touring-ready vehicle builds.
Use only products/brands currently sold in South Africa and listed in the research brief context.
Do not advertise international-only variants not available in SA.
Do not invent prices, stock levels, lead times, or warranties.

CRITICAL product-visual rule for product ads:
If a reference product image is provided by user attachment, the model must match that product exactly.
Repeat in prompt wording that attachment is source of truth and must be followed strictly.
No colour swaps, no badge/logo swaps, no geometry changes, no added/removed hardware."""

TONE = (
    "Confident, technical, premium, practical South African 4x4 voice. "
    "Authority without hype. Engineering clarity over generic promo fluff."
)

SERVICES_LIST = """Suspension and fitment solutions for key SA platforms (Toyota Hilux/Fortuner/Land Cruiser, Ford Ranger, Suzuki Jimny, Isuzu D-Max where applicable).
4x4 protection and armour categories: replacement bumpers, sliders, underbody protection.
Recovery and touring support categories: winch/recovery accessories and off-road support hardware where in brief.
Brand families to prioritize only when relevant and SA-available per brief: EFS, Tough Dog, Formula 4x4, Onca, MCC, Wildog, Takla, De Graaf, Opposite Lock distributed lines.
Avoid generic camping-heavy narratives unless explicitly in client brief for that post."""

TARGET_MARKETS = """South African 4x4 owners and overlanders in Gauteng and nearby regions.
Primary personas: serious overlanders, technical enthusiasts, bakkie owners needing load-correct fitment, and premium build customers wanting reliable component selection.
Buying triggers: product authenticity, fitment correctness, harsh-road durability, and trust in local support."""

PHOTOGRAPHY_STYLE = """Photorealistic South African off-road fitment realism.
Use premium workshop or grounded outdoor contexts depending on pillar.
Product ads must clearly show true hardware details.
No CGI plastic look, no fantasy accessories, no random part substitutions.

For product-image ads with a user attachment, include these constraints explicitly in the prompt:
1) Study the attached image in strict detail.
2) Study the attached image in strict detail again before rendering.
3) Match exact product shape, colour, branding, finish, and hardware layout.
4) Do not alter, stylize, simplify, or "improve" the product.
5) Do not add/remove parts; attachment is the source of truth."""


def main() -> None:
    db.init_db()
    cid = db.find_client_id_by_name_substring(MATCH_SUBSTRING)
    if cid is None:
        cid = db.add_client(
            COMPANY_NAME,
            INDUSTRY,
            BRAND_CONTEXT,
            TONE,
            services_list=SERVICES_LIST,
            target_markets=TARGET_MARKETS,
            photography_style=PHOTOGRAPHY_STYLE,
        )
        print(f"Created client id={cid} ({COMPANY_NAME}).")
    else:
        db.update_client(
            int(cid),
            company_name=COMPANY_NAME,
            industry=INDUSTRY,
            brand_context=BRAND_CONTEXT,
            tone=TONE,
            services_list=SERVICES_LIST,
            target_markets=TARGET_MARKETS,
            photography_style=PHOTOGRAPHY_STYLE,
        )
        print(f"Updated client id={cid} ({COMPANY_NAME}).")


if __name__ == "__main__":
    main()
