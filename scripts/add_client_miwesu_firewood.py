"""One-off: add Miwesu Firewood client to agency.db (placeholder DNA — refine when research lands)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

import database as db  # noqa: E402


def main() -> None:
    db.init_db()
    name = "Miwesu Fire wood"
    for row in db.get_all_clients():
        if "miwesu" in str(row.get("company_name", "")).lower():
            print(f"Already in database: {row['company_name']} (id={row['id']})")
            return

    cid = db.add_client(
        name,
        industry="Retail — firewood, braai fuel & outdoor burning (South Africa)",
        brand_context=(
            "PLACEHOLDER — research in progress. Independent firewood supplier focused on "
            "seasoned, ready-to-burn wood for homes, hospitality, and weekend braais. "
            "Positioning, proof points, competitors, and guarantees will be updated when "
            "brand research is complete. Do not invent specific claims until client brief is finalized."
        ),
        tone=(
            "Warm, trustworthy, straightforward; local and approachable; safety-conscious "
            "(storage, sparks, dry wood); South African English."
        ),
        services_list=(
            "Seasoned firewood bundles (retail bags); bulk/stacked quantities; "
            "braai wood & kindling (to be confirmed); delivery vs pickup (TBD); "
            "commercial vs residential (TBD)."
        ),
        target_markets=(
            "Homeowners with fireplaces/braais; weekend entertainers; hospitality venues; "
            "campers and outdoor hosts; value- and quality-conscious buyers in the service area (TBD)."
        ),
        photography_style=(
            "Documentary retail realism: stacked splits, mesh retail bags, bark texture, "
            "natural daylight or warm workshop light; shallow depth of field on grain and bark; "
            "avoid plastic HDR and fake campfire CGI; authentic South African context when location shots are used."
        ),
    )
    print(f"Created client: {name!r} — id={cid}")


if __name__ == "__main__":
    main()
