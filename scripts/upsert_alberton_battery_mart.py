"""
Upsert Alberton Battery Mart brand fields into agency.db.

Usage (repo root):
    uv run python scripts/upsert_alberton_battery_mart.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import database as db  # noqa: E402

COMPANY_NAME = "Alberton Battery Mart"
MATCH_SUBSTRING = "alberton battery mart"

INDUSTRY = (
    "Automotive and backup power battery specialist — mobile replacement, diagnostics, fitment, "
    "and commercial/fleet support (Alberton, South Africa)."
)

BRAND_CONTEXT = """Official business identity: Alberton Battery Mart (independent local specialist, not national "Battery Mart SA" and not First Battery Centre).
Website: https://www.albertonbatterymart.co.za/
Primary location (for captions): 28 St Columb Rd, New Redruth, Alberton, 1450. Phone: 010 109 6211. WhatsApp: +27 82 304 6926.
Trading hours: Mon-Fri 08:00-17:00, Sat 08:00-12:00, Sun closed.

Core promise: fast, technically-correct battery solutions with free diagnostics and fitment; mobile callouts across Alberton/New Redruth/Meyersdal and nearby industrial zones where approved.

Core categories:
- Automotive batteries (standard flooded, EFB, AGM for Start/Stop)
- Truck/commercial batteries
- Motorcycle / powersport batteries
- Deep-cycle / solar / inverter backup batteries
- Gate motor and alarm batteries (12V 7Ah class)

Service authority:
- Free battery + alternator testing (Midtronics-style diagnostic workflow)
- Professional fitment
- BMS coding/registering where required for modern vehicles
- Mobile fitment/callout during trading hours

Brand strategy priorities:
- Feature Eco Plus and Power Plus frequently in promotional/value posts
- Also stock and use fitment-accurate alternatives (Willard, Exide, Enertec) when relevant
- Never invent stock, prices, warranties, or turnaround promises outside approved brief
- Position as technical authority: "right battery for your vehicle and duty cycle", not discount hype.
"""

TONE = """Direct, practical, high-trust, technically clear. Local SA English. Emergency-helpful but calm.
Speak like a battery specialist diagnosing the full charging system, not a generic salesperson.
No fake urgency, fake discounts, or exaggerated claims."""

SERVICES_LIST = """Primary products:
- Eco Plus batteries (priority promo line)
- Power Plus batteries (priority promo line)
- Willard, Exide, Enertec (fitment-accurate alternatives)

Services:
- Free battery testing
- Free alternator testing
- Professional fitment
- Mobile callout battery replacement (approved local areas)
- BMS coding/registration for compatible modern vehicles
- Truck/commercial battery support
- Deep-cycle/solar backup battery guidance
- Gate motor and alarm battery replacement
"""

TARGET_MARKETS = """Alberton, New Redruth, Meyersdal, Brackenhurst, Randhart, Alberton Central, Alrode,
and nearby Germiston trade/fleet zones when approved.
Segments:
1) Private motorists with urgent non-start problems and Start/Stop battery needs.
2) SMEs and trade vehicles needing quick uptime.
3) Fleet/commercial operators focused on reducing downtime.
4) Homeowners needing reliable backup power and gate/alarm battery continuity."""

PHOTOGRAPHY_STYLE = """Photorealistic Alberton Battery Mart — clean modern-industrial SA workshop (reference photography on file).

LOCATION LOOK (match the real shop, not a generic garage):
- VERY CLEAN spaces: minimalist, organized, bright—avoid greasy, junk-stacked, horror-movie workshop clichés.
- Interior materials: exposed LIGHT FACE BRICK (warm tan / soft orange / beige), FLOATED CEMENT or polished concrete
  floors, thick FLOATED CEMENT countertops on brick bases, occasional smooth grey wall paint, CHARCOAL / SLATE
  feature walls behind counters and logo areas.
- Lighting: daylight through roller doors and/or skylights + clean overhead LED/fluoro—airy, premium, high-trust.
- Structure: dark steel beams, corrugated roof, large open bays—professional retail-grade fit-out.
- Storefront (exterior shots): light brick + dark corrugated metal header band, large white dimensional lettering,
  clean concrete apron, open workshop bays.
- Optional context: marine/boat in bay, commercial bakkie, passenger cars with bonnet open—always battery/diagnostics story first.

Allowed scenes:
- under-bonnet battery bay fitment inside the clean workshop
- service counter / reception (floated cement + light brick + dark feature wall)
- diagnostic tester on terminals; alternator/charging system context where believable
- battery product hero on neutral dark bench OR on-brand display rack
- mobile callout roadside replacement
- fleet/commercial rack context
- deep-cycle/backup installation (realistic cabling, safety)

Visual rules:
- realistic human hands/tools, no fake CGI plastics
- clear terminal orientation and plausible cabling
- battery focus—no tyre tread hero shots, no tyre SKU confusion
- no phones, tablets, chat UI, or app screens in image prompts (WhatsApp stays in copy only).
"""


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

