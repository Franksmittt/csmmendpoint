# Alberton Tyre Clinic — Brand Bible (CrewAI + CRM)

Derived from their **Next.js / Tailwind / Shadcn** frontend (`tailwind.config.ts`, `globals.css`, page copy) and condensed for social generation. Use this as the single source of truth when editing the client row in SQLite / Streamlit.

---

## 1. One-line positioning

**Premium, family-run fitment and safety specialists since 1989 (New Redruth, Alberton).**  
Hook: *“Don’t Just Change Tyres. Invest in Safety.”*  
Promise: *“We prioritize your safety over sales, guaranteed.”*

---

## 2. Paste into CRM (exact blocks)

### Industry (short)

`Independent automotive retail — tyres, brakes, shocks, alignment, batteries (Alberton, South Africa)`

### Brand context

> Alberton Tyre Clinic is a premium, family-run vehicle maintenance centre established in **1989** (**36-year heritage**). Core philosophy: **“Invest in Safety”** and **“We prioritize safety over sales.”** Location: **New Redruth, Alberton**. Official focus on premium brands: **Pirelli**, **Michelin**, **ATE Brakes**, **Bilstein Shocks**, **Willard Batteries**. Flagship lead magnet: **FREE 6-Point Vehicle Safety Check** (tyres, shocks, brakes, battery, etc.) — *no obligation, no hassle*.  
> **Visual identity (for any image brief):** dark charcoal / near-black environments, **Tyre Orange accent `#F17924`** (CTAs, rim light, neon edge light), high-contrast *premium garage* photography, mechanical precision — **not** a bright discount-yard look. Typography on-site: **Geist** family; headers are **bold / extrabold, often uppercase** — mirror that *feel* in overlay wording (short, confident).  
> **Contact:** 011 907 8495 · WhatsApp 081 884 9807.

### Tone / voice

> Authoritative, safety-obsessed, honest, community-driven. Sound like a **trusted fitment engineer** protecting families — **not** a generic discount tyre shop. Lean on **generational trust in Alberton**, **precision fitment**, and **honest assessment**. Avoid cheap-sales jargon, hypey CAPS spam, and “cheapest in town” positioning.

### Services / brands (full list)

> **Brands:** Pirelli, Michelin, ATE Brakes, Bilstein Shocks, Willard Batteries.  
> **Services:** 3D wheel alignment, balancing & rotation, brake pad & disc replacement, shock absorber fitment, tyre sales & fitment, batteries, **FREE 6-Point Safety Check**.  
> **Rotating promotions (verify before posting):** e.g. free alignment *check* with any 4 new tyres; **15% off ATE brake pad & disc replacement**; **R200 cashback** on Willard batteries — only advertise what is **currently** approved.

### Target markets

> Safety-conscious **families**, daily **commuters**, and **premium vehicle owners** in **Alberton** who want **honest, generational expertise** — not quick-fix discount churn.

### Photography & visual style (dedicated CRM field)

Paste into the dashboard **Photography & visual style** box (or run `scripts/upsert_alberton_brand.py`, which syncs this same block):

> Documentary-style, authentic South African tyre fitment centre. STRICTLY NO glossy, sterile, or futuristic CGI laboratory looks. Floors: Black interlocking industrial rubber tiles with raised coin texture, visible seams, and light dust/debris. Include flush, bright orange metal lift platforms. Walls: Matte painted walls with a 3-band scheme (dark charcoal bottom, thin safety orange middle stripe, light grey top) featuring visible conduits and tools, OR exposed red/brown face brick. Equipment: Heavy-duty red-and-black tyre changers and balancers (like Corghi or Hunter), stacks of tyres on the floor, and a lived-in look with brooms or drink cans. Lighting & Camera: Mixed lighting with long fluorescent ceiling tubes and high-contrast natural daylight spilling from large open roll-up garage doors. Camera: DSLR, 50mm to 85mm lens, wide aperture feel—AGGRESSIVELY blur and soften mid-to-far background (strong bokeh on distant bays, racks, and door light); hero subject plane only tack-sharp; avoid deep-focus everything-sharp stock look. Realistic shadows. Human elements: Staff in black work uniforms (dark tees/trousers). Bare hands/forearms with natural light grease and dust. NO FACES, NO GLOVES.

---

## 3. Mandatory image prompt clause

Every `Image_Generation_Prompt` for this client must read as **premium + dark + orange accent**. Append a clause equivalent to:

> *High-contrast, low-key lighting; dark charcoal / near-black background or premium garage setting; vibrant Tyre Orange **#F17924** accents or rim lighting; clean, mechanical, authoritative — not a budget tyre yard.*

Respect **aspect ratio** from post format (1:1 vs 9:16) as already required by tasks.

---

## 4. Copy guardrails

### Do

- Tie claims to **safety**, **heritage (since 1989 / 36 years)**, **family-run**, **Alberton / New Redruth**.
- Name **specific brands** (Pirelli, Michelin, ATE, Bilstein, Willard) only when accurate for the post.
- Use assessment language: **free check**, **no obligation**, **honest report**.

### Don’t

- Generic “cheap tyres”, “lowest prices”, “crazy deals”, stock-photo vibes in *copy* (image prompt already bans discount-yard look).
- Invent promotions not in `services_list` / current brief — **staleness risk**.

### Signature phrases (rotate, don’t paste every post)

- *“Don’t Just Change Tyres. Invest in Safety.”*
- *“Alberton’s trusted family-run fitment experts since 1989.”*
- *“Safety over sales — guaranteed.”*

---

## 5. Dashboard “Content pillar” → ATC focus

| CRM pillar | Alberton focus |
|------------|----------------|
| **Service Highlight** | Free 6-Point Safety Check; alignment / balancing; shock or brake *inspection* story |
| **Did You Know? / Educational** | Why premium tyres or ATE brakes matter on local roads; tread / stopping distance; battery health |
| **Promotional / Sale** | Approved offers only: ATE % off, Willard cashback, alignment check with 4 tyres, etc. |
| **Brand Authority** | 36-year heritage, family business, official dealer brands, **4.9★** social proof (if still accurate) |

---

## 6. Suggested overlay (Heading / Footer) style

- **Heading:** Short, **uppercase or title case**, safety or heritage — e.g. `INVEST IN SAFETY` / `36 YEARS IN ALBERTON`.
- **Footer:** CTA or proof — e.g. `FREE 6-POINT CHECK` · `BOOK TODAY` · `NEW REDRUTH`.

Keep strings **short** for programmatic stamping.

---

## 7. Quick test brief (Promotional / Sale)

- **Client:** Alberton Tyre Clinic  
- **Pillar:** Promotional / Sale  
- **Topic:** **15% off ATE brake pad & disc replacement** (confirm offer live before publish)  
- **Expected vibe:** authoritative, safety-first, premium garage, orange accent imagery, no discount-shop tone.

---

## 8. Maintenance

When the Next.js site changes offers, colours, or copy: update **this file**, then sync CRM fields (or run `scripts/upsert_alberton_brand.py` from repo root).
