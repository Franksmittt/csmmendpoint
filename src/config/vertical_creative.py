"""
Vertical routing for CrewAI: automotive (tyre retail) vs firewood / solid fuel (Miwesu).

Keeps tyre-specific image rules out of firewood posts and encodes Miwesu audience,
messaging, and visual variety (not every image is a mesh bag).
"""

from __future__ import annotations

from typing import Literal

VerticalMode = Literal["firewood", "battery", "automotive"]

# Single source of truth from "WHAT THE WOOD LOOKS LIKE" research — prompt engineering for
# generative image models (rejects Northern Hemisphere pine/oak/birch defaults).
MIWESU_WOOD_VISUAL_SPEC = """
ENGINEERED HEAT — XYLOLOGICAL IMAGE RULES (any log, split, stack, or macro wood in frame MUST obey):

BASELINE — NOT TEMPERATE FIREWOOD: Ban pale pine/poplar, papery birch bark, open-pored beige oak,
light “airy” logs, soft fibrous split faces with long stringy splinters, or pastel European timber.
This is Southern African bushveld hardwood: extreme density (reads visually as heavy, mineral, stone-like).
Light reflects off the surface; it does not glow through the wood—matte or waxy/leather-like sheen,
NOT soft subsurface translucency, NOT plastic/wax toy look.

SPLIT FACE & FRACTURE: Prefer short-grain, rugged, almost conchoidal breaks—sharp ridges and solid
terrain, NOT fuzzy hairy oak/pine tear patterns. Split faces often look burnished, hard, non-porous.

HYPER-DRY / END GRAIN: Very dry hardwood shows radial CHECKS—dark sharp cracks from pith toward bark
on the circular end; this is proof of dryness, not a flaw. Heartwood colours are SATURATED: deep oxide
reds, chocolate browns, ochre yellows—never washed-out green-wet or pastel beige.

BARK (GENERAL): Thick, integrated armour—fused to wood, NOT paper sheets peeling. Rugged silhouette
with deep shadow in furrows; high-contrast sunlight helps read depth (soft flat light reads as plastic).

SPECIES — match product when post names a line (else “SA hardwood mix” may blend traits truthfully):

• GEELHAAK (Camel Thorn / Vachellia erioloba): Irregular cross-sections (ovals, wedges)—not perfect
  cylinders. Bark: deep dusty grey to blackish-brown, CANYON-LIKE deep longitudinal furrows, blocky corky
  ridges; silvery weathering possible on highlights. Thorn SCARS: straight greyish thorns with swollen
  bulbous bases (paired nodes along stem) even if tips snapped. SPLIT FACE: dark purple-brown heartwood
  (~#3B2F2F) with a SHARP bright straw-yellow sapwood ring (~#E4D96F)—high-contrast “halo”; homogeneous
  dense grain (not oak growth rings); end grain may show tiny dark gum/mineral flecks. Surface: smooth,
  waxy, stone-ceramic. BURN / COALS (if fire): blocky deep red coals holding shape; flame blue-orange base,
  steady low-flicker; thin bluish wispy smoke—NO heavy white steam or grey smoulder from “wet” wood.

• KNOPPIESDORING (Senegalia nigrescens): Silhouette BUMPY—conical woody knobs (~2–3 cm), often with
  small hooked black thorn on knob tip; knuckle rhythm. Bark: very dark brown to black, scabrous/sandpaper
  between knobs. SPLIT: near-black espresso heartwood (~#231F20) with pale cream sapwood (~#F5F5DC);
  interlocked grain can look RAGGED/torn on split face—tough, resistant. Coals: bright orange-white,
  long-lasting.

• SEKELBOS (Sickle Bush / Dichrostachys cinerea): Smaller diameters (branchy), twisted/tangled stacks;
  often rounds or half-splits. SIGNATURE “TARGET” END GRAIN: grey-brown bark ring → BROAD MUSTARD/OCHRE
  sapwood (~#FFDB58)—vibrant, not beige → russet/reddish-brown core (~#80461B). Bark: yellow-grey to
  grey-brown, finer vertical fissures, thinner than Geelhaak. Spine stubs: woody branchlets at ~90°.
  Split face: slight OILY / SATIN sheen (griller aromatic)—smoother specular than other species.

• SNUIFPEUL (Vachellia nilotica): Bark LATTICE / braided plates (fissures split and rejoin), blackish-grey.
  Heartwood brick-red / warm reddish-brown (~#A04030); sapwood pale beige-white. Thinner paired straight
  thorns. Optional prop: constricted “beaded” seed pods for species storytelling.

COMBUSTION (when flames/coals): Dense SA hardwood—blue/clean base of flame, minimal steam, steady flame;
  coals glow deep red-gold and retain log structure; fine pale ash optional—NOT instant crumble to grey dust.

PROMPT TACTIC: Name the species or “South African Camel Thorn / knobthorn / sickle bush hardwood” in BOTH
Image_Generation_Prompt_1_1 and Image_Generation_Prompt_9_16 when showing wood; explicitly forbid pine, birch,
oak, or generic light split logs.
Never describe OLED displays, smartphones, or app interfaces—those are unrelated to firewood photography.
""".strip()


def _name_slug(client: dict) -> str:
    return str(client.get("company_name") or "").strip().lower()


def is_firewood_vertical(client: dict) -> bool:
    slug = _name_slug(client)
    if "miwesu" in slug:
        return True
    if "alberton tyre clinic" in slug or "alberton battery mart" in slug:
        return False
    blob = " ".join(
        [
            str(client.get("company_name") or ""),
            str(client.get("industry") or ""),
            str(client.get("brand_context") or ""),
        ]
    ).lower()
    return any(
        k in blob
        for k in (
            "firewood",
            "fire wood",
            "braai wood",
            "miwesu",
        )
    )


def is_battery_vertical(client: dict) -> bool:
    slug = _name_slug(client)
    if "alberton battery mart" in slug:
        return True
    if "alberton tyre clinic" in slug or "miwesu" in slug:
        return False
    blob = " ".join(
        [
            str(client.get("company_name") or ""),
            str(client.get("industry") or ""),
            str(client.get("brand_context") or ""),
            str(client.get("services_list") or ""),
        ]
    ).lower()
    return (
        not is_firewood_vertical(client)
        and any(
            k in blob
            for k in (
                "battery",
                "batteries",
                "alternator",
                "bms coding",
                "mobile battery",
                "deep cycle",
                "start/stop",
            )
        )
    )


def is_non_tyre_vertical(client: dict) -> bool:
    return is_firewood_vertical(client) or is_battery_vertical(client)


def get_vertical_mode(client: dict) -> VerticalMode:
    if is_firewood_vertical(client):
        return "firewood"
    if is_battery_vertical(client):
        return "battery"
    return "automotive"


def get_vertical_creative_rules_for_tasks(client: dict) -> str:
    """Inject into tasks.yaml as {vertical_creative_rules}."""
    if is_firewood_vertical(client):
        return _FIREWOOD_VERTICAL_BLOCK.format(
            company=client.get("company_name", "Miwesu Fire Wood"),
            wood_visual_spec=MIWESU_WOOD_VISUAL_SPEC,
        )
    if is_battery_vertical(client):
        return _BATTERY_VERTICAL_BLOCK.format(
            company=client.get("company_name", "Alberton Battery Mart"),
            battery_workshop_visual_spec=BATTERY_WORKSHOP_VISUAL_SPEC,
        )
    if not is_firewood_vertical(client):
        return (
            "VERTICAL=automotive (tyre retail). Use all tyre co-brand, tread, fitment-bay, "
            "and PRODUCT ENFORCEMENT (tire model) rules in the task exactly. "
            "featured_brand / brand_models apply when not None. "
            "MECHANICAL REALISM: never depict a loose tyre carcass alone on a spin balancer—tyre must be "
            "mounted on an alloy or steel rim (mag) with bead seated; the wheel assembly spins on the balancer. "
            "Alignment/tracking: wheels on the vehicle on the rack or believable gauge hardware—never a floating "
            "tyre-only on an alignment rig."
        )
    return ""


_FIREWOOD_VERTICAL_BLOCK = """
VERTICAL=firewood (Miwesu solid fuel — NOT automotive). IGNORE tyre tread, sidewall, tyre mounting,
fitment bay oil, wheel balancing, and any tire SKU / brand_models list for IMAGE or CAPTION unless
the text explicitly says they are irrelevant for this mode. Do NOT mention Continental, Michelin,
Dunlop tyres, etc. This client sells FIREWOOD and BRAAI WOOD in Gauteng.

IMAGE SUBJECT LOCK (NON-NEGOTIABLE): Both image prompts may show ONLY real-world fuel / heat /
outdoor-kitchen subjects: SA hardwood logs, splits, mesh bags, braai grids, flames, coals, smoke (thin),
fireplaces, closed stoves, driveway stacks, bakkie delivery, patio/boma (no faces if brief forbids),
or abstract geometry suggesting heat (glow gradients, ember light on matte black cyclorama).
STRICTLY FORBIDDEN IN THE FRAME (even as “lifestyle”): smartphones, cellphones, tablets, laptops,
smartwatches, app UI, WhatsApp/chat bubbles, messaging screenshots, OLED/TV/computer screens, generic
office tech, or “hand holding phone”. Ordering is via WhatsApp in COPY only—never illustrate the app
or device. Do NOT use the words OLED, squircle, or phone-adjacent UI metaphors in the image prompt.

BRAND & OFFER (truth from client brief — never invent prices, MOQs, or suburbs not in brand_context):
• Site: miwesufirewood.co.za | Taglines: Heat. Redefined. / Engineered Heat. | WhatsApp orders + COD.
• Product lines to name when relevant: Geelhaak Hardwood; The Ultimate Braai Mix; Premium Sekelbos
  (with 10 kg / 20 kg / 30 kg bags, MOQs, and R25 / R50 / R70 from services_list / brand_context).
• Quality story: kiln-dried / verified dry positioning (<12% moisture narrative where stated).
• Delivery: Gauteng; zones; estate / gate logistics; next-day where possible — only as in brief.

PRIMARY AUDIENCE (paid social + premium positioning):
Affluent Gauteng households who braai year-round and heat with wood—estates and secure suburbs
(Sandton, Centurion, Pretoria east, East Rand e.g. Bedfordview, Alberton/Meyersdal, Midrand, etc.),
English and Afrikaans-first homes, high trust in COD and WhatsApp fulfilment. They fear WET WOOD,
wasted spend, and messy drops. Speak to: braai culture, flavour/coals, load-shedding resilience
(backup heat without sounding alarmist), HOA-friendly low-smoke dry wood, convenience of bulk delivery.
Keep copy inclusive and premium—avoid demographic slurs; "affluent Gauteng homeowners" is enough.

CAPTION VOICE: Confident, precise, warm—"engineered heat" not cheesy campfire clichés. SA English;
Afrikaans flavour only if natural short phrase. No fake discounts or competitions unless in brief.

IMAGE VARIETY (CRITICAL — do NOT show a retail mesh bag in every post):
Rotate concepts so the feed feels art-directed, not repetitive:
1) Product hero: precision-split hardwood, white woven mesh bag, bronze/ember rim light (Hardware Noir).
2) Flame & coals: braai grid, glowing coals, steak-adjacent sizzle (no tyre metaphors).
3) Hearth / winter: closed-combustion stove or fireplace glass, Highveld evening—premium interior.
4) Delivery truth: driveway stack, bakkie offload, estate gate context (no faces if brief forbids).
5) Educational macro: end-grain rings, bark texture, moisture clarity—minimal negative space.
6) Lifestyle: patio/boma at dusk, social braai silhouette—firewood IMPLIED or subtle prop, not always bag.
7) Abstract: ink-black / matte black cyclorama, ember-orange rim light, subtle teal accent—pure heat
   geometry; NO screens, NO devices, NO UI—must still read as fire/energy not tech product.

As long as the image clearly reads FIREWOOD / BRAAI / HEARTH / HEAT in South African premium context,
bags are OPTIONAL. Ban generic American log-cabin stock, plastic HDR fire, or tyre workshop confusion.

=== WOOD IN FRAME — COPY THIS XYLOLOGY INTO BOTH PROMPTS VERBATIM (adapt species to post) ===
{wood_visual_spec}
=== END XYLOLOGY ===

WOOD REALISM: Every prompt field that shows logs, splits, stacks, bark macro, or end grain
must implement the block above—species-accurate Southern African hardwood, not AI-default temperate wood.
Never describe dripping wet logs for a "delivery" hero. Glass on modern stoves stays plausible.

JSON: Suggested_Text_Overlay Heading/Footer must sound on-brand (Heat. Redefined. / Engineered Heat.
energy optional—not every line).
""".strip()


# Alberton Battery Mart — real workshop / storefront visual DNA (from site photography).
BATTERY_WORKSHOP_VISUAL_SPEC = """
WORKSHOP & LOCATION LOOK (NON-NEGOTIABLE for in-store / bay scenes): This is a VERY CLEAN modern South African
battery workshop—not a greasy, cluttered old garage. Default interior palette:
• Walls: exposed LIGHT FACE BRICK in warm tan / soft orange / beige (neat mortar joints), sometimes paired with
  smooth cool grey painted walls or a CHARCOAL / SLATE feature wall behind service counters or logo.
• Floors + counters: FLOATED CEMENT / polished concrete—smooth, matte-grey, lightly mottled; thick floated-cement
  countertops on brick bases; minimal clutter; professional retail finish.
• Structure: dark steel beams, corrugated roof sections, translucent skylight panels, large roller doors with
  bright daylight spill—airy, high-trust, premium industrial.
• Exterior (if storefront): light brick facade + dark corrugated metal header band; large white 3D block lettering;
  open workshop bays; clean concrete apron.
• Reception/coffee-station corners (if shown): same materials—light brick + floated cement, dark accent wall—
  consistent with the workshop brand world.
NEGATIVE / AVOID for workshop prompts: oily black floors, stacked junk, "American NASCAR" garage clichés, tyre-wall
heroes, random tyres, phone screens, or grimy horror-movie workshops. Keep it bright, organized, and architected.
""".strip()


_BATTERY_VERTICAL_BLOCK = """
VERTICAL=battery (automotive energy storage + diagnostics — NOT tyre retail). IGNORE tyre tread, tyre sidewall,
fitment-bay tyre mounting, wheel balancing, and any tyre SKU / tire model list.

PRIMARY SETTING — {company}: When either image prompt shows the shop, service counter, or indoor service bay,
implement the workshop look below (copy key phrases into both prompts—do not invent a different building style).

=== WORKSHOP VISUAL DNA — copy into BOTH prompts for interior/exterior location shots ===
{battery_workshop_visual_spec}
=== END WORKSHOP DNA ===

IMAGE SUBJECT LOCK (NON-NEGOTIABLE): Both prompts may show only battery-relevant real scenes:
car/truck battery products, under-bonnet battery bays, terminal cleaning, Midtronics-style tester diagnostics,
alternator test context, mobile callout van fitment, roadside rescue, workshop bench, deep-cycle/solar backup
batteries, gate/alarm backup batteries, fleet/commercial battery racks.
FORBIDDEN: tyres/wheels/tread closeups, phone screens, chat UI overlays, fake app mockups, laptop scenes.
If WhatsApp is mentioned, keep it in caption copy only (CTA), not as phone-in-hand imagery.

BRAND & OFFER: Use only facts from services_list + brand_context. Prioritize: free battery and alternator testing,
professional fitment, mobile callout (areas from brief), Start/Stop AGM/EFB guidance, BMS coding when relevant,
commercial/truck + deep-cycle/solar where listed.

PRODUCT PRIORITY: If brand_context/services_list include focus brands, prefer those naturally.
For Alberton Battery Mart strategy, prioritize Eco Plus and Power Plus in promo/feature posts while still allowing
Willard/Exide/Enertec where needed for fitment accuracy and trust positioning.

AUDIENCE: Alberton / New Redruth / Meyersdal + nearby industrial/commercial (e.g., Alrode, Germiston) depending
on brief. Cover both private motorists (urgent non-start) and fleet/trade customers (downtime cost, reliability).

CAPTION VOICE: Fast, practical, technical clarity. Local SA English. High-trust, no hype. No fake discounts or
invented warranties/specs.

VISUAL VARIETY (do not repeat one setup):
1) Product hero battery on neutral dark set (true labels visible, realistic casing and terminals).
2) In-car battery bay fitment scene inside the CLEAN workshop (light brick + floated cement visible in background).
3) Diagnostic shot (tester connected + readable result context).
4) Mobile rescue/callout roadside scene.
5) Fleet/commercial rack + heavy-duty battery context.
6) Deep-cycle/backup power setup (non-gimmicky, real cables and safety posture).
7) Service counter / reception moment: floated cement counter, brick base, charcoal feature wall, brand-true signage
   (no readable fake fine print).

REALISM: No CGI plastic renders, no impossible cable routing, no wrong terminal orientation, no random engine parts.
""".strip()


def get_research_vertical_hint(client: dict) -> str:
    """Shorter addition for research_task."""
    if is_battery_vertical(client):
        return (
            "Battery vertical: non-start pain, alternator/battery diagnostics, Start/Stop AGM/EFB fitment, "
            "mobile callout response, fleet downtime prevention, and local suburb service trust. "
            "Workshop imagery: ultra-clean modern SA fit-out—light face brick, floated cement counters/floors, "
            "charcoal feature walls, bright daylight—not a grimy generic garage."
        )
    if not is_firewood_vertical(client):
        return (
            "Automotive vertical: surface tyre-adjacent angles, fitment trust, co-brand when applicable."
        )
    return (
        "Firewood vertical: braai culture, dry-wood anxiety, Gauteng delivery logistics, estate access, "
        "seasonal winter heating spike, premium hardwood species names from services_list—never tyre SKUs. "
        "Surface xylological accuracy: Geelhaak/Knoppiesdoring/Sekelbos/Snuifpeul visual signatures vs "
        "generic pine/oak/birch (see vertical_creative_rules wood block)."
    )
