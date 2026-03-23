"""
Placeholder: upsert Absolute Offroad into agency.db when research is ready.

Usage (repo root):
    uv run python scripts/upsert_absolute_offroad.py

Add PUBLISHER_QUEUE_CLIENTS fragment (e.g. absolute offroad) in `.env` so the
publisher link can include this client after onboarding.
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

# TODO: Replace with approved research (site, services, tone, markets).
INDUSTRY = "Automotive / 4x4 — off-road accessories and fitment (South Africa)."

BRAND_CONTEXT = """TBD: trading name, locations, core categories (lift kits, recovery, tyres, etc.),
proof points, and compliance rules. Do not invent stock, prices, or warranties."""

TONE = "TBD: confident, technical, adventure-capable — match final brand voice."

SERVICES_LIST = "TBD: list real services and product lines after research."

TARGET_MARKETS = "TBD: primary service areas and customer segments."

PHOTOGRAPHY_STYLE = "TBD: workshop, trail, product hero — align with brand deck."


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
