"""
Tire manufacturer co-brand vault for CrewAI — slogans, visual compliance, target psychology.

Sourced from internal research: "Tire Brand Deep Dive for Social Media" (SA fitment context).
Do not use as legal brand approval; always verify against official brand portals for live campaigns.
"""

from __future__ import annotations

FEATURED_BRAND_NONE = "None"

# Key = display name for UI / prompts. Value = structured profile.
# top_models = SA high-velocity stock lines for product enforcement in CrewAI (no invented SKUs).
TIRE_BRAND_GUIDELINES: dict[str, dict[str, str]] = {
    "Apollo": {
        "top_models": (
            "Apterra AT2 (robust budget A/T); Alnac 4G (hatch/sedan touring); "
            "Amazer 4G Life (extreme longevity commuter)."
        ),
        "slogan": "Practical grip and reliable tread for everyday harsh-road use.",
        "visual_rules": (
            "Primary identifier: Apollo Purple (PMS 2603C). Prefer horizontal logo lockup; "
            "black logo variant only when colour printing unavailable. Use purple as bold "
            "accent disruptor vs typical tyre-industry red/yellow noise."
        ),
        "target_psychology": (
            "Smart economics—budget-conscious professionals who still demand daily safety "
            "and reliability; transparency over hype."
        ),
    },
    "BFGoodrich": {
        "top_models": (
            "All-Terrain T/A KO2/KO3; Mud-Terrain T/A KM3; Trail-Terrain T/A."
        ),
        "slogan": "Built, not bought. (Platform: What Are You Building For? / Your Next.)",
        "visual_rules": (
            "Persian Red HEX #CC3433 as hero accent. Gritty, authentic, UGC-style—not glossy "
            "showroom. Celebrate fabrication, overlanding, mud, dust, bakkies and 4x4 capability."
        ),
        "target_psychology": (
            "Hardcore 4x4, off-road, and bakkie owners; identity-led buyers who build rigs "
            "rather than buy status."
        ),
    },
    "Bridgestone": {
        "top_models": (
            "Dueler A/T 002 (Bakkies/SUVs); Turanza T005 (Sedans); "
            "Ecopia EP422/EP150 (Eco/Commuters)."
        ),
        "slogan": "Solutions for your journey.",
        "visual_rules": (
            "Corporate palette: strong red/black structured campaigns; sustainability and "
            "'journey' motifs (roads, landscapes). Hero-hub-hygiene friendly—educational + "
            "aspirational travel imagery."
        ),
        "target_psychology": (
            "Safety-conscious and sustainability-minded drivers; comfort, handling, wet/dry "
            "performance narrative."
        ),
    },
    "Continental": {
        "top_models": (
            "CrossContact AT3/ATR (4x4s); PremiumContact 6/7 (Premium Sedans); "
            "SportContact 7 (Ultra-High Performance)."
        ),
        "slogan": "Safe, convenient, sustainable solutions.",
        "visual_rules": (
            "STRICT: Continental Yellow HEX #e38704 (RGB 227/135/4) only against Continental "
            "Black #000000 and White—clinical German engineering look. Prancing horse logo: "
            "maintain protection space (~half logo height); never distort or graduate behind logo. "
            "Clean, scientific, high-contrast—not cluttered co-op mashups."
        ),
        "target_psychology": (
            "Precision-focused premium drivers; top-tier braking and safety confidence; "
            "local travel/safety tips resonate in SA."
        ),
    },
    "Dunlop": {
        "top_models": (
            "Grandtrek AT3G/AT5 (tough bakkies); SP Sport FM800/LM705 (daily hatchbacks, e.g. VW Polo); "
            "SP Sport Maxx 060+ (UHP)."
        ),
        "slogan": "Taking You Beyond.",
        "visual_rules": (
            "Flying D emblem + wordmark. Palette: Dunlop Yellow #FEDE00, Red #FF0000, "
            "Process Black #000000, Cool Gray 9 #808080. On busy photos use yellow panel "
            "behind logo for legibility."
        ),
        "target_psychology": (
            "Daily commuters, commercial fleets, and legacy brand loyalists; local heritage "
            "and weather-aware messaging (e.g. Highveld storms)."
        ),
    },
    "Falken": {
        "top_models": (
            "Wildpeak A/T3WA/A/T4W; Ziex ZE310 Ecorun; Azenis FK510/FK520."
        ),
        "slogan": (
            "Born on the track, bred on the mountains, raised on the podium. "
            "Race tested, road ready."
        ),
        "visual_rules": (
            "Motorsport energy: track days, drifting, Nürburgring heritage cues—affordable UHP "
            "performance aesthetic; visceral motion, not static catalogue shots."
        ),
        "target_psychology": (
            "Younger drivers and tuning enthusiasts seeking affordable performance and "
            "credible motorsport DNA."
        ),
    },
    "Firestone": {
        "top_models": (
            "Destination A/T Grip (budget 4x4s); Roadhawk; FS100 Touring."
        ),
        "slogan": "Backed by Bridgestone—dependable heritage at accessible positioning.",
        "visual_rules": (
            "Alizarin Crimson HEX #EC1E2F as bold, urgent accent; bright readable layouts. "
            "Heritage American pneumatic pioneer story; trustworthy family/commercial vibe."
        ),
        "target_psychology": (
            "Pragmatic families and cost-conscious fleet managers; reliability and "
            "historical trust over flash."
        ),
    },
    "General Tire": {
        "top_models": (
            "Grabber AT3 (undisputed mid-tier A/T king); Grabber X3; Altimax One S."
        ),
        "slogan": "Rugged all-terrain dominance—Grabber range.",
        "visual_rules": (
            "Red Pantone 187C (approx HEX #A6192E from RGB 166,25,46) with Black and White. "
            "Respect logo hierarchy: stacked primary, horizontal secondary, shield only when "
            "full wordmark appears elsewhere; ~20% logo-width clear space."
        ),
        "target_psychology": (
            "Off-road and bakkie buyers wanting Continental-backed durability; holiday "
            "trip / gravel-road confidence."
        ),
    },
    "Goodyear": {
        "top_models": (
            "Wrangler Duratrac RT / All-Terrain Adventure (Off-road); "
            "EfficientGrip Performance 2 (quiet highway); Eagle F1 Asymmetric 6 (luxury/UHP)."
        ),
        "slogan": "Protect Our Good Name.",
        "visual_rules": (
            "Wingfoot symbol (Hermes/Mercury heritage)—speed and motion. Emphasize tread "
            "durability, pothole and harsh-road resilience, all-season versatility; pair "
            "with speedy professional fitment narrative."
        ),
        "target_psychology": (
            "Commuters and fleet users needing toughness on unpredictable SA roads; trust "
            "in supply chain and longevity."
        ),
    },
    "Hankook": {
        "top_models": "Dynapro AT2/Xtreme; Ventus Prime 3/4; Kinergy Eco 2.",
        "slogan": "Driving Emotion.",
        "visual_rules": (
            "Modern Korean high-tech lifestyle brand: dynamic compositions, outdoor/camping "
            "crossover cues where relevant; innovation and R&D story."
        ),
        "target_psychology": (
            "Tech-savvy value buyers who respect contemporary Korean engineering; lifestyle "
            "bundles and analytical proof points."
        ),
    },
    "Kumho": {
        "slogan": "Comfort, longevity, ESG-minded value.",
        "visual_rules": (
            "KT Red #EF0010, KT Silver #B4B7B9, KT Dark Gray #4A4A49, KT Gold #4C4C4E. "
            "Logo needs strong contrast—white background preferred; no rotation, no line "
            "through logo, no clutter inside mandated clear space."
        ),
        "target_psychology": (
            "Family SUV owners prioritizing ride comfort, low noise, mileage, and pragmatic cost."
        ),
    },
    "Maxxis": {
        "top_models": "Razr AT/MT; Bravo A/T 700/771; Premitra/Victra Series.",
        "slogan": "Maxxis is the tire of choice.",
        "visual_rules": (
            "Champion / Olympic / extreme-sport association; bifurcate mud-terrain aggression "
            "for bakkies vs sporting pedigree for passenger lines—high-energy, not sterile."
        ),
        "target_psychology": (
            "Off-roaders and younger active lifestyles; also reliable commuter angle on "
            "passenger range."
        ),
    },
    "Michelin": {
        "top_models": (
            "Primacy 4+/5 (longevity/sedans); LTX Trail/Force (Bakkies); Pilot Sport 5 (performance)."
        ),
        "slogan": "Motion for Life.",
        "visual_rules": (
            "Bibendum (Michelin Man) is sacred—use only authorized assets from Michelin Brand "
            "Center; no recreation or off-model characters. Visual story: TCO, fuel efficiency, "
            "longevity, safety, emotional warmth."
        ),
        "target_psychology": (
            "Buyers who invest for total cost of ownership—premium upfront acceptable for "
            "fuel savings, mileage, and supreme safety perception."
        ),
    },
    "Pirelli": {
        "top_models": (
            "Scorpion All Terrain Plus/ATR (luxury 4x4s); Cinturato P7 (executive sedans); "
            "P Zero (supercars/UHP)."
        ),
        "slogan": "Power is Nothing Without Control.",
        "visual_rules": (
            "STRICTLY dark backgrounds for logo lockups—never yellow or red behind Pirelli "
            "logotype; avoid bright dealer colours that mimic Pirelli corporate palette. "
            "Long P logotype min width 15mm in print rules—on social, maintain clear, "
            "unmolested wordmark. High contrast, sleek, luxury, Formula 1 prestige—moody "
            "lighting acceptable; never cheap or discount visual language."
        ),
        "target_psychology": (
            "Luxury SUV and performance saloon owners; motorsport and aesthetic prestige; "
            "control and Italian engineering excellence."
        ),
    },
    "Radar": {
        "top_models": "Renegade RT/AT; Dimax Sport; Dimax Sprint.",
        "slogan": "Premium tires at affordable prices.",
        "visual_rules": (
            "Carbon-neutral brand story (since 2013). SA: Proteas / Cricket South Africa "
            "partnership—national team, green credentials, accessible premium positioning."
        ),
        "target_psychology": (
            "Value seekers who reject 'cheap unsafe' stigma; cricket fans and "
            "environmentally conscious younger drivers."
        ),
    },
    "Royal Black": {
        "top_models": "Royal Performance; Royal Mile; Royal A/T.",
        "slogan": "World-class value.",
        "visual_rules": (
            "Simple, high-readability layouts; transparent pricing cues; testimonial-forward. "
            "No faux-luxury—honest entry-level replacement narrative."
        ),
        "target_psychology": (
            "Entry-level buyers under cost pressure; reassurance via warranty, local proof, "
            "and basic safety on rough roads."
        ),
    },
    "Yokohama": {
        "top_models": (
            "Geolandar A/T G015 (bakkies/SUVs); ADVAN Sport (UHP); BluEarth-Es ES32 (eco/commuters). "
            "(Aligned with SA market research — verify local stock.)"
        ),
        "slogan": "Excellence by nature. (Mission: enrich lives through beneficial products.)",
        "visual_rules": (
            "Japanese engineering + sustainability + YX2026 tech (EV-ready narrative). "
            "Dual lane: motorsport/drift energy AND family safety comfort."
        ),
        "target_psychology": (
            "JDM enthusiasts and performance drivers alongside pragmatic families wanting "
            "trusted daily grip."
        ),
    },
}


def format_brand_guidelines_for_prompt(brand_name: str) -> str:
    """Human-readable block for CrewAI task interpolation."""
    if not brand_name or brand_name.strip() == FEATURED_BRAND_NONE:
        return (
            "No featured manufacturer tire brand for this run. Mention tyre brands only when "
            "they appear in the client's services_list or brand_context; do not apply external "
            "manufacturer vault rules."
        )
    profile = TIRE_BRAND_GUIDELINES.get(brand_name.strip())
    if not profile:
        return f"Unknown brand key {brand_name!r}; ignore vault."
    return (
        f"Brand: {brand_name}\n"
        f"Slogan / mission line: {profile['slogan']}\n"
        f"Visual & compliance rules: {profile['visual_rules']}\n"
        f"Target psychology: {profile['target_psychology']}"
    )


def format_brand_models_for_prompt(brand_name: str) -> str:
    """SA high-velocity tire lines for CrewAI `{brand_models}` interpolation (product enforcement)."""
    if not brand_name or brand_name.strip() == FEATURED_BRAND_NONE:
        return (
            "No featured manufacturer tire brand for this run. Do not invent specific tire model "
            "names or SKUs. Reference tyres only if they appear verbatim in the client's "
            "services_list or brand_context."
        )
    profile = TIRE_BRAND_GUIDELINES.get(brand_name.strip())
    if not profile:
        return (
            f"Unknown brand key {brand_name!r} — no vault model list. Do not invent tire model "
            "names; use only products named in services_list or brand_context."
        )
    top = (profile.get("top_models") or "").strip()
    if not top:
        return (
            f"No top_models vault entry for {brand_name!r}. Do not invent SKUs; use only names "
            "from services_list or brand_context."
        )
    return (
        f"AUTHORIZED {brand_name} tire models — choose exactly ONE that best fits the "
        f"content pillar and target audience; copy naming faithfully: {top}"
    )


def featured_brand_select_options() -> list[str]:
    return [FEATURED_BRAND_NONE] + sorted(TIRE_BRAND_GUIDELINES.keys())
