"""Refresh Miwesu Fire Wood client DNA from Miwesu wood/ research pack (agency.db)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

import database as db  # noqa: E402
from config.vertical_creative import MIWESU_WOOD_VISUAL_SPEC  # noqa: E402

CLIENT_SUBSTRING = "miwesu"


def main() -> None:
    db.init_db()
    cid = None
    for row in db.get_all_clients():
        if CLIENT_SUBSTRING in str(row.get("company_name", "")).lower():
            cid = int(row["id"])
            break
    if cid is None:
        raise SystemExit("No client matching 'miwesu' — run add_client_miwesu_firewood.py first.")

    db.update_client(
        cid,
        company_name="Miwesu Fire Wood",
        industry=(
            "Premium firewood & braai wood — Gauteng delivery, orders via website that hands off to "
            "WhatsApp; pay on delivery (COD). (Do not use tech-stack names in image prompts.)"
        ),
        brand_context=(
            "Official site: https://miwesufirewood.co.za | Farm / brand link: https://www.miwesu.co.za. "
            "Taglines: 'Heat. Redefined.' and 'Engineered Heat.' Positioning: premium, precision-split "
            "hardwood — not roadside commodity. Core anxiety to solve: fear of wet wood; promise "
            "kiln-dried / verified dry wood with moisture transparency (<12% moisture guarantee per "
            "site positioning). Sustainably framed: invasive-species removal where applicable (eco-positive "
            "narrative). "
            "PRODUCT LINE (use exact names): (1) Geelhaak Hardwood — balanced burn, bright flames, "
            "steady heat, Blue Thorn / Geelhaak story. (2) The Ultimate Braai Mix — hand-selected mix "
            "of SA hardwoods (Snuifpeul, Knoppiesdoring, Geelhaak, Sekelbos), gourmet aroma, long coals. "
            "(3) Premium Sekelbos — sickle bush, low moisture, clean hot burn, braai/camping/high heat. "
            "Sizes & public pricing (10 kg bag R25, MOQ 50 bags | 20 kg bag R50, MOQ 40 | 30 kg bag R70, "
            "MOQ 20). Product slugs: geelhaak-10/20/30, braai-mix-10/20/30, sekelbos-10/20/30. "
            "Educational woods content on site also covers Knoppiesdoring, Snuifpeul, Mopane, Rooibos — "
            "use only when relevant to the post. "
            "ORDERING: Website form opens WhatsApp with order details; primary WhatsApp +27 73 030 9679; "
            "secondary +27 72 717 2572; email orders@miwesufirewood.co.za. No online card checkout — "
            "confirm on WhatsApp; COD on delivery. Next-day slots where possible. "
            "No walk-in shop street address for captions — online/WhatsApp ordering and Gauteng delivery only; "
            "do not invent a physical shop address. "
            "DELIVERY: Gauteng only; zones A/B/C with free delivery in qualifying conditions; 47+ suburb "
            "landing pages (Sandton, Bryanston, Alberton, Midrand, Pretoria East, Centurion, etc.). "
            "Do not claim delivery to excluded areas. "
            "CREATIVE GUARDRAILS: Visual brand is 'Hardware Noir' — deep matte black backdrops (NOT OLED/"
            "phone/screen metaphors), bronze/copper rim light, ember orange & teal accents, clean modern "
            "typography in overlays only—wood as engineered thermal product. NEVER depict smartphones, "
            "WhatsApp UI, or gadgets in social image prompts; ordering is text-only. "
            "Social copy can be premium and precise without sounding cold; braai culture and load-shedding "
            "backup are valid SA hooks. Audience: affluent Gauteng homeowners who braai year-round and heat "
            "with wood—estates, secure suburbs, Sandton/Centurion/Pretoria east/East Rand/Midrand-type "
            "contexts; English-first with natural Afrikaans touches when brief allows. Keep captions "
            "inclusive and premium (no demographic slurs). "
            "IMAGE BRIEF: Not every post must show a mesh bag—as long as the image clearly reads firewood, "
            "braai heat, hearth, or premium engineered fuel (flames, coals, delivery, macro texture, abstract "
            "Hardware Noir). Wood depiction must follow SA bushveld xylology in photography_style "
            "(Engineered Heat spec)—never default to pine/oak/birch or pale temperate logs. "
            "Do not invent promotions, prices, or moisture readings not stated "
            "above; do not fabricate reviews or guarantees beyond site policy."
        ),
        tone=(
            "Confident, precise, premium — 'engineered heat' not folksy cliché. Warm undertone (fire, "
            "gathering, flavour). South African English; short punchy lines for Stories, richer for Feed. "
            "Optional Afrikaans angle only when brief asks — keep technical terms clear."
        ),
        services_list=(
            "Geelhaak Hardwood 10/20/30 kg; The Ultimate Braai Mix 10/20/30 kg; Premium Sekelbos 10/20/30 kg. "
            "MOQ: 50 (10kg) / 40 (20kg) / 20 (30kg) bags. WhatsApp order workflow; COD pay on delivery. "
            "Free delivery in qualifying Gauteng zones; delivery policy + suburb pages on site. "
            "Moisture-quality story (<12%); sustainable / invasive-removal narrative. "
            "Wood Finder / education: species pages (Geelhaak, Sekelbos, Mopane, Rooibos, Knoppiesdoring, Snuifpeul)."
        ),
        target_markets=(
            "Gauteng homeowners with braais, fireplaces, pizza ovens, fire pits; load-shedding backup cooks; "
            "weekend entertainers and 'braai masters'; gated estates and security-conscious suburbs; "
            "hospitality venues needing reliable dry fuel; quality-conscious buyers avoiding wet roadside wood."
        ),
        photography_style=(
            "Hardware Noir / cinematic product: deep void black or titanium panels (#000, #1C1C1E), bronze "
            "rim light (#BF953F gradient accents), ember orange (#FF7F50) and teal (#00A8A8) as controlled "
            "highlights — match miwesufirewood.co.za energy. Wood = precision thermal hardware: tack-sharp "
            "bark and end-grain, shallow DOF (~f/1.2–f/1.4 language), slow hero scale on texture. "
            "White woven mesh retail bags are authentic product truth when showing SKUs—but rotate concepts: "
            "also use flames-only, coals on grid, closed-combustion stove glass, driveway delivery, "
            "macro end-grain/bark, or ink-black cyclorama with ember-edge glow — variety like a curated "
            "campaign, not the same bag every post. "
            "No plastic HDR, no fake campfire CGI, no stock 'American cabin' cliché unless brief demands; "
            "prefer high-end SA patio / braai context when lifestyle shots appear. "
            "FORBIDDEN in generated image prompts: phones, tablets, app UIs, OLED/screen imagery, "
            "squircle device aesthetics. Stove/fireplace GLASS (flames visible) is OK—consumer electronics are not. "
            "\n\n"
            + MIWESU_WOOD_VISUAL_SPEC
        ),
    )
    print(f"Updated client id={cid} (Miwesu Fire Wood) from research pack.")


if __name__ == "__main__":
    main()
