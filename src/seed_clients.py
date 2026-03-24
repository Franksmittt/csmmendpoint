"""
Default clients for empty databases (Streamlit Cloud / fresh clone).

Source of truth matches scripts/upsert_alberton_brand.py, upsert_alberton_battery_mart.py,
add_client_miwesu_firewood.py — keep in sync when brand briefs change.
"""

from __future__ import annotations

import database as db

# --- Alberton Tyre Clinic (from scripts/upsert_alberton_brand.py) ---

ATC_COMPANY = "Alberton Tyre Clinic"

ATC_INDUSTRY = (
    "Independent automotive retail — tyres, brakes, shocks, alignment, batteries "
    "(Alberton, South Africa)"
)

ATC_BRAND_CONTEXT = """Alberton Tyre Clinic is a premium, family-run vehicle maintenance centre established in 1989 (36-year heritage). Core philosophy: "Invest in Safety" and "We prioritize safety over sales." Physical address (for captions and maps): 26 St Columb St, New Redruth, Alberton, Gauteng 1449. Area: New Redruth, Alberton. Website: https://albertontyreclinic.co.za/ — Official focus on premium brands: Pirelli, Michelin, ATE Brakes, Bilstein Shocks, Willard Batteries. Flagship lead magnet: FREE 6-Point Vehicle Safety Check (tyres, shocks, brakes, battery, etc.) — no obligation, no hassle.

Visual identity (for any image brief): dark charcoal / near-black environments, Tyre Orange accent #F17924 (CTAs, rim light, neon edge light), high-contrast premium garage photography, mechanical precision — not a bright discount-yard look. Typography on-site: Geist family; headers are bold / extrabold, often uppercase — mirror that feel in overlay wording (short, confident).

Contact (use exactly in social captions): Phone 011 907 8495 · WhatsApp 081 884 9807."""

ATC_TONE = """Authoritative, safety-obsessed, honest, community-driven. Sound like a trusted fitment engineer protecting families — not a generic discount tyre shop. Lean on generational trust in Alberton, precision fitment, and honest assessment. Avoid cheap-sales jargon, hypey CAPS spam, and "cheapest in town" positioning."""

ATC_SERVICES = """Brands: Pirelli, Michelin, ATE Brakes, Bilstein Shocks, Willard Batteries.

Services: 3D wheel alignment, balancing & rotation, brake pad & disc replacement, shock absorber fitment, tyre sales & fitment, batteries, FREE 6-Point Safety Check.

Rotating promotions (verify before posting): e.g. free alignment check with any 4 new tyres; 15% off ATE brake pad & disc replacement; R200 cashback on Willard batteries — only advertise what is currently approved."""

ATC_MARKETS = """Safety-conscious families, daily commuters, and premium vehicle owners in Alberton who want honest, generational expertise — not quick-fix discount churn."""

ATC_PHOTO = """Documentary-style, authentic South African tyre fitment centre. STRICTLY NO glossy, sterile, or futuristic CGI laboratory looks. Floors: Black interlocking industrial rubber tiles with raised coin texture, visible seams, and light dust/debris. Include flush, bright orange metal lift platforms. Walls: Matte painted walls with a 3-band scheme (dark charcoal bottom, thin safety orange middle stripe, light grey top) featuring visible conduits and tools, OR exposed red/brown face brick. Equipment: Heavy-duty red-and-black tyre changers and balancers (like Corghi or Hunter), stacks of tyres on the floor, and a lived-in look with brooms or drink cans. Lighting & Camera: Mixed lighting with long fluorescent ceiling tubes and high-contrast natural daylight spilling from large open roll-up garage doors. Camera: DSLR, 50mm to 85mm lens, wide aperture feel—AGGRESSIVELY blur and soften mid-to-far background (strong bokeh on distant bays, racks, and door light); hero subject plane only tack-sharp; avoid deep-focus everything-sharp stock look. Realistic shadows. Human elements: Staff in black work uniforms (dark tees/trousers). Bare hands/forearms with natural light grease and dust. NO FACES, NO GLOVES."""

# --- Alberton Battery Mart (from scripts/upsert_alberton_battery_mart.py) ---

ABM_COMPANY = "Alberton Battery Mart"

ABM_INDUSTRY = (
    "Automotive and backup power battery specialist — mobile replacement, diagnostics, fitment, "
    "and commercial/fleet support (Alberton, South Africa)."
)

ABM_BRAND_CONTEXT = """Official business identity: Alberton Battery Mart (independent local specialist, not national "Battery Mart SA" and not First Battery Centre).
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

ABM_TONE = """Direct, practical, high-trust, technically clear. Local SA English. Emergency-helpful but calm.
Speak like a battery specialist diagnosing the full charging system, not a generic salesperson.
No fake urgency, fake discounts, or exaggerated claims."""

ABM_SERVICES = """Primary products:
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

ABM_MARKETS = """Alberton, New Redruth, Meyersdal, Brackenhurst, Randhart, Alberton Central, Alrode,
and nearby Germiston trade/fleet zones when approved.
Segments:
1) Private motorists with urgent non-start problems and Start/Stop battery needs.
2) SMEs and trade vehicles needing quick uptime.
3) Fleet/commercial operators focused on reducing downtime.
4) Homeowners needing reliable backup power and gate/alarm battery continuity."""

ABM_PHOTO = """Photorealistic Alberton Battery Mart — clean modern-industrial SA workshop (reference photography on file).

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

# --- Miwesu (from scripts/add_client_miwesu_firewood.py) ---

MIWESU_COMPANY = "Miwesu Fire wood"

MIWESU_INDUSTRY = "Retail — firewood, braai fuel & outdoor burning (South Africa)"

MIWESU_BRAND = (
    "PLACEHOLDER — research in progress. Independent firewood supplier focused on "
    "seasoned, ready-to-burn wood for homes, hospitality, and weekend braais. "
    "Positioning, proof points, competitors, and guarantees will be updated when "
    "brand research is complete. Do not invent specific claims until client brief is finalized."
)

MIWESU_TONE = (
    "Warm, trustworthy, straightforward; local and approachable; safety-conscious "
    "(storage, sparks, dry wood); South African English."
)

MIWESU_SERVICES = (
    "Seasoned firewood bundles (retail bags); bulk/stacked quantities; "
    "braai wood & kindling (to be confirmed); delivery vs pickup (TBD); "
    "commercial vs residential (TBD)."
)

MIWESU_MARKETS = (
    "Homeowners with fireplaces/braais; weekend entertainers; hospitality venues; "
    "campers and outdoor hosts; value- and quality-conscious buyers in the service area (TBD)."
)

MIWESU_PHOTO = (
    "Documentary retail realism: stacked splits, mesh retail bags, bark texture, "
    "natural daylight or warm workshop light; shallow depth of field on grain and bark; "
    "avoid plastic HDR and fake campfire CGI; authentic South African context when location shots are used."
)

# --- Absolute Offroad (from scripts/upsert_absolute_offroad.py) ---

AO_COMPANY = "Absolute Offroad"

AO_INDUSTRY = "4x4 accessories and fitment specialist — South African market (Alberton)."

AO_BRAND_CONTEXT = """Absolute Offroad is a South African 4x4 specialist focused on technical fitment and real-world overlanding upgrades.
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

AO_TONE = (
    "Confident, technical, premium, practical South African 4x4 voice. "
    "Authority without hype. Engineering clarity over generic promo fluff."
)

AO_SERVICES = """Suspension and fitment solutions for key SA platforms (Toyota Hilux/Fortuner/Land Cruiser, Ford Ranger, Suzuki Jimny, Isuzu D-Max where applicable).
4x4 protection and armour categories: replacement bumpers, sliders, underbody protection.
Recovery and touring support categories: winch/recovery accessories and off-road support hardware where in brief.
Brand families to prioritize only when relevant and SA-available per brief: EFS, Tough Dog, Formula 4x4, Onca, MCC, Wildog, Takla, De Graaf, Opposite Lock distributed lines.
Avoid generic camping-heavy narratives unless explicitly in client brief for that post."""

AO_MARKETS = """South African 4x4 owners and overlanders in Gauteng and nearby regions.
Primary personas: serious overlanders, technical enthusiasts, bakkie owners needing load-correct fitment, and premium build customers wanting reliable component selection.
Buying triggers: product authenticity, fitment correctness, harsh-road durability, and trust in local support."""

AO_PHOTO = """Photorealistic South African off-road fitment realism.
Use premium workshop or grounded outdoor contexts depending on pillar.
Product ads must clearly show true hardware details.
No CGI plastic look, no fantasy accessories, no random part substitutions.

For product-image ads with a user attachment, include these constraints explicitly in the prompt:
1) Study the attached image in strict detail.
2) Study the attached image in strict detail again before rendering.
3) Match exact product shape, colour, branding, finish, and hardware layout.
4) Do not alter, stylize, simplify, or "improve" the product.
5) Do not add/remove parts; attachment is the source of truth."""


def apply_seed_clients() -> None:
    """Insert default clients when the clients table is empty."""
    db.add_client(
        ATC_COMPANY,
        ATC_INDUSTRY,
        ATC_BRAND_CONTEXT,
        tone=ATC_TONE,
        services_list=ATC_SERVICES,
        target_markets=ATC_MARKETS,
        photography_style=ATC_PHOTO,
    )
    db.add_client(
        ABM_COMPANY,
        ABM_INDUSTRY,
        ABM_BRAND_CONTEXT,
        tone=ABM_TONE,
        services_list=ABM_SERVICES,
        target_markets=ABM_MARKETS,
        photography_style=ABM_PHOTO,
    )
    db.add_client(
        MIWESU_COMPANY,
        MIWESU_INDUSTRY,
        MIWESU_BRAND,
        tone=MIWESU_TONE,
        services_list=MIWESU_SERVICES,
        target_markets=MIWESU_MARKETS,
        photography_style=MIWESU_PHOTO,
    )
    db.add_client(
        AO_COMPANY,
        AO_INDUSTRY,
        AO_BRAND_CONTEXT,
        tone=AO_TONE,
        services_list=AO_SERVICES,
        target_markets=AO_MARKETS,
        photography_style=AO_PHOTO,
    )
