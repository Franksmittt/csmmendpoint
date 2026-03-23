"""
Push Alberton Tyre Clinic brand bible fields into agency.db.

Usage (repo root):
    uv run python scripts/upsert_alberton_brand.py

Matches clients where company_name contains "Alberton Tyre Clinic" (case-insensitive).
If none found, prints instructions — add the client in Streamlit first, or use add_client.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import database as db  # noqa: E402

INDUSTRY = (
    "Independent automotive retail — tyres, brakes, shocks, alignment, batteries "
    "(Alberton, South Africa)"
)

BRAND_CONTEXT = """Alberton Tyre Clinic is a premium, family-run vehicle maintenance centre established in 1989 (36-year heritage). Core philosophy: "Invest in Safety" and "We prioritize safety over sales." Physical address (for captions and maps): 26 St Columb St, New Redruth, Alberton, Gauteng 1449. Area: New Redruth, Alberton. Website: https://albertontyreclinic.co.za/ — Official focus on premium brands: Pirelli, Michelin, ATE Brakes, Bilstein Shocks, Willard Batteries. Flagship lead magnet: FREE 6-Point Vehicle Safety Check (tyres, shocks, brakes, battery, etc.) — no obligation, no hassle.

Visual identity (for any image brief): dark charcoal / near-black environments, Tyre Orange accent #F17924 (CTAs, rim light, neon edge light), high-contrast premium garage photography, mechanical precision — not a bright discount-yard look. Typography on-site: Geist family; headers are bold / extrabold, often uppercase — mirror that feel in overlay wording (short, confident).

Contact (use exactly in social captions): Phone 011 907 8495 · WhatsApp 081 884 9807."""

TONE = """Authoritative, safety-obsessed, honest, community-driven. Sound like a trusted fitment engineer protecting families — not a generic discount tyre shop. Lean on generational trust in Alberton, precision fitment, and honest assessment. Avoid cheap-sales jargon, hypey CAPS spam, and "cheapest in town" positioning."""

SERVICES_LIST = """Brands: Pirelli, Michelin, ATE Brakes, Bilstein Shocks, Willard Batteries.

Services: 3D wheel alignment, balancing & rotation, brake pad & disc replacement, shock absorber fitment, tyre sales & fitment, batteries, FREE 6-Point Safety Check.

Rotating promotions (verify before posting): e.g. free alignment check with any 4 new tyres; 15% off ATE brake pad & disc replacement; R200 cashback on Willard batteries — only advertise what is currently approved."""

TARGET_MARKETS = """Safety-conscious families, daily commuters, and premium vehicle owners in Alberton who want honest, generational expertise — not quick-fix discount churn."""

PHOTOGRAPHY_STYLE = """Documentary-style, authentic South African tyre fitment centre. STRICTLY NO glossy, sterile, or futuristic CGI laboratory looks. Floors: Black interlocking industrial rubber tiles with raised coin texture, visible seams, and light dust/debris. Include flush, bright orange metal lift platforms. Walls: Matte painted walls with a 3-band scheme (dark charcoal bottom, thin safety orange middle stripe, light grey top) featuring visible conduits and tools, OR exposed red/brown face brick. Equipment: Heavy-duty red-and-black tyre changers and balancers (like Corghi or Hunter), stacks of tyres on the floor, and a lived-in look with brooms or drink cans. Lighting & Camera: Mixed lighting with long fluorescent ceiling tubes and high-contrast natural daylight spilling from large open roll-up garage doors. Camera: DSLR, 50mm to 85mm lens, wide aperture feel—AGGRESSIVELY blur and soften mid-to-far background (strong bokeh on distant bays, racks, and door light); hero subject plane only tack-sharp; avoid deep-focus everything-sharp stock look. Realistic shadows. Human elements: Staff in black work uniforms (dark tees/trousers). Bare hands/forearms with natural light grease and dust. NO FACES, NO GLOVES."""

MATCH_SUBSTRING = "Alberton Tyre Clinic"


def main() -> None:
    db.init_db()
    cid = db.find_client_id_by_name_substring(MATCH_SUBSTRING)
    if cid is None:
        print(
            f"No client found with name containing {MATCH_SUBSTRING!r}. "
            "Onboard the client in Streamlit, then re-run this script."
        )
        sys.exit(1)
    db.update_client(
        cid,
        industry=INDUSTRY,
        brand_context=BRAND_CONTEXT,
        tone=TONE,
        services_list=SERVICES_LIST,
        target_markets=TARGET_MARKETS,
        photography_style=PHOTOGRAPHY_STYLE,
    )
    print(f"Updated client id={cid} with Alberton Tyre Clinic brand bible fields.")


if __name__ == "__main__":
    main()
