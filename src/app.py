"""Endpoint Media CRM — Streamlit dashboard (CrewAI + SQLite)."""

import html
import io
import json
import os
import random
import sys
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

load_dotenv(_SRC.parent / ".env")

import database as db
from config.brand_vault import (
    FEATURED_BRAND_NONE,
    featured_brand_select_options,
    format_brand_guidelines_for_prompt,
    format_brand_models_for_prompt,
)
from config.vertical_creative import (
    get_research_vertical_hint,
    get_vertical_creative_rules_for_tasks,
    get_vertical_mode,
    is_battery_vertical,
    is_firewood_vertical,
    is_non_tyre_vertical,
)
from crew import SocialMediaCrew
from json_utils import parse_crew_json

# Design tokens — classical / editorial (warm paper, ink, navy & bronze)
C_BG = "#f5f0e8"
C_SURFACE = "#fffcf7"
C_TEXT = "#2c2416"
C_TEXT_BODY = "#4a433a"
C_MUTED = "#6b6459"
C_BORDER = "#cdc6b9"
C_INPUT_BG = "#fffdf8"
C_PRIMARY = "#1e3a5f"
C_ACCENT = "#7c5c36"
C_HEADING = "#1c1917"
C_SUCCESS = "#2f5f46"
# Legacy aliases (emphasis on light backgrounds)
C_WHITE = C_HEADING
C_ACCENT_YELLOW = C_ACCENT
C_ATHENS = C_TEXT_BODY
C_GRAY = C_MUTED
C_BLUE = C_PRIMARY
C_SHARK = "#ebe6dc"
C_CONFIDENCE = C_SUCCESS

VIEW_DASHBOARD = "Dashboard"
VIEW_ONBOARD = "New client"
VIEW_OVERLAY = "Overlay studio"

# Titan-style HTML exporter (html2canvas) — embedded in Overlay studio.
_TITAN_EXPORTER_HTML = Path(__file__).resolve().parent.parent / "static" / "titan_ad_exporter.html"

POST_FORMAT_OPTIONS = (
    "Standard Feed Post (1:1 Ratio)",
    "Story Format (9:16 Ratio - short text)",
)

CONTENT_PILLAR_OPTIONS = (
    "Service Highlight",
    "Did You Know? / Educational",
    "Promotional / Sale",
    "Brand Authority",
)

# Generation Hub — session keys so Auto-Pilot can sync dropdowns + rerun.
EM_HUB_POST_FORMAT = "em_hub_post_format"
EM_HUB_PILLAR = "em_hub_content_pillar"
EM_HUB_BRAND = "em_hub_featured_brand"
EM_HUB_HOOK = "em_hub_creative_hook"
EM_HUB_BATCH = "em_hub_batch_count"
EM_HUB_BATTERY_LINE = "em_hub_battery_featured_line"
# Set by Auto-Pilot button; applied at hub container start (before keyed widgets).
EM_PENDING_AUTOPILOT = "em_pending_autopilot"
# Sidebar-selected client (replaces main-area selectbox; scales to many clients).
EM_ACTIVE_CLIENT_ID = "em_active_client_id"

# One-click variety pack: each post randomizes format, pillar, brand & hook.
MIXED_PACK_POST_COUNT = 3

# Randomized in batch mode — shapes hook without changing the formal pillar.
CREATIVE_HOOK_OPTIONS = (
    "Quick tip, trick, or hack the reader can use today",
    "‘Did you know?’ curiosity hook plus one concrete fact",
    "Service spotlight: name one specific offering and who it helps",
    "Promo pulse: urgency, seasonal, or value framing (stay truthful)",
    "Authority / trust: proof, experience, or credibility signal",
    "Myth-bust or ‘here’s what actually happens’ educational contrast",
    "Product hero: brand-new tyre—pedestal, road, or minimal set; vault colours; real rubber shine",
    "Workshop moment: fitment bay—honest light; new OR worn tyres as the story demands",
)

# Firewood / solid fuel — no tyre metaphors in hooks (mixed packs & Auto-Pilot use these).
FIREWOOD_CREATIVE_HOOK_OPTIONS = (
    "Quick tip: storing splits, lighting a clean fire, or keeping hardwood dry",
    "‘Did you know?’ hook plus one fact about braai heat, coals, or wood density",
    "Service spotlight: one concrete line—bag size, MOQ, delivery zone, or WhatsApp order flow",
    "Promo pulse: seasonal cold, bulk order, or estate delivery framing (stay truthful to brief)",
    "Authority / trust: dry wood, consistency, COD fulfilment—no invented awards",
    "Myth-bust: wet wood vs seasoned hardwood; smoke vs clean burn",
    "Product hero: precision splits, mesh bag, bronze/ember rim light—Hardware Noir premium fuel",
    "Delivery truth: driveway stack, bakkie offload, gate context—no bag required every time",
    "Lifestyle / boma: dusk flames, coals on grid, heat implied—braai culture without cliché stock",
    "Abstract premium: OLED-black set, ember edge light—reads as engineered heat, not random fire stock",
    "Educational macro: SA hardwood xylology—deep bark furrows, heartwood/sapwood halo, radial checks on end grain; forbid pine/oak/birch look",
)

BATTERY_CREATIVE_HOOK_OPTIONS = (
    "Emergency non-start rescue angle: fast test, right fitment, back on road",
    "Technical trust angle: free battery + alternator diagnostics before replacement",
    "Start/Stop education: AGM/EFB fitment matters, avoid incorrect downgrades",
    "Mobile callout angle: Alberton/New Redruth/Meyersdal response and convenience",
    "Product spotlight: Eco Plus or Power Plus value-focused battery hero",
    "Fleet/commercial angle: truck/commercial uptime, reduce downtime risk",
    "Backup power angle: deep-cycle/solar/gate battery reliability story",
    "Myth-bust: voltage alone is not health; conductance/testing proves condition",
)

BATTERY_FEATURED_LINE_OPTIONS = (
    "Eco Plus",
    "Power Plus",
    "Willard",
    "Exide",
    "Enertec",
)


def _creative_hook_options_for_client(client: dict) -> tuple[str, ...]:
    if is_battery_vertical(client):
        return BATTERY_CREATIVE_HOOK_OPTIONS
    return (
        FIREWOOD_CREATIVE_HOOK_OPTIONS
        if is_firewood_vertical(client)
        else CREATIVE_HOOK_OPTIONS
    )


def _battery_line_options_for_client(client: dict) -> tuple[str, ...]:
    if not is_battery_vertical(client):
        return ("Auto",)
    return ("Auto",) + BATTERY_FEATURED_LINE_OPTIONS

# Onboarding widget keys (read on Initialize click)
OB_COMPANY = "ob_company_name"
OB_INDUSTRY = "ob_industry"
OB_SERVICES = "ob_services_list"
OB_MARKETS = "ob_target_markets"
OB_CONTEXT = "ob_brand_context"
OB_TONE = "ob_tone"
OB_PHOTOGRAPHY = "ob_photography_style"


def _inject_classical_theme() -> None:
    """Classical editorial UI: warm paper, serif headings, restrained navy & bronze."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=Source+Sans+3:wght@400;500;600&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <style>
          html, body, .stApp, [data-testid="stAppViewContainer"] {{
            background-color: {C_BG} !important;
            color: {C_TEXT_BODY} !important;
            font-family: 'Source Sans 3', 'Segoe UI', system-ui, sans-serif !important;
            font-size: 17px !important;
          }}
          [data-testid="stHeader"] {{
            background-color: {C_SURFACE} !important;
            border-bottom: 1px solid {C_BORDER} !important;
          }}
          .block-container {{
            padding-top: 1.25rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px !important;
          }}
          .main .block-container p, .main .block-container li, .main label,
          .main [data-testid="stWidgetLabel"] p {{
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 17px !important;
          }}
          .main h1 {{
            font-size: 2rem !important;
            color: {C_HEADING} !important;
            font-family: 'Crimson Pro', 'Georgia', serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em;
          }}
          .main h2, .main h3, .main h4 {{
            color: {C_PRIMARY} !important;
            font-family: 'Crimson Pro', 'Georgia', serif !important;
            font-weight: 600 !important;
          }}
          .stCaption, [data-testid="stCaption"] {{
            color: {C_MUTED} !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 0.92rem !important;
          }}

          section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #faf6ef 0%, {C_SURFACE} 100%) !important;
            border-right: 1px solid {C_BORDER} !important;
          }}
          section[data-testid="stSidebar"] .block-container {{
            padding-top: 0.75rem !important;
            width: 100% !important;
          }}
          .ui-sidebar-title {{
            font-family: 'Crimson Pro', Georgia, serif !important;
            font-size: 1.45rem !important;
            font-weight: 600 !important;
            color: {C_HEADING} !important;
            margin: 0 0 0.15rem 0;
            line-height: 1.15;
            letter-spacing: -0.02em;
          }}
          .ui-sidebar-heading {{
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: {C_MUTED} !important;
            margin: 0.75rem 0 0.4rem 0;
          }}
          section[data-testid="stSidebar"] .stButton > button {{
            border-radius: 6px !important;
            min-height: 40px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            font-family: 'Source Sans 3', sans-serif !important;
            width: 100% !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding-left: 12px !important;
          }}
          section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
            background-color: {C_PRIMARY} !important;
            color: #faf8f5 !important;
            border: 1px solid {C_PRIMARY} !important;
          }}
          section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
            background-color: {C_SURFACE} !important;
            color: {C_TEXT} !important;
            border: 1px solid {C_BORDER} !important;
          }}
          section[data-testid="stSidebar"] hr {{
            border-color: {C_BORDER} !important;
            margin: 0.75rem 0 !important;
          }}

          .stButton > button {{
            border-radius: 6px !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 16px !important;
            font-weight: 500 !important;
          }}
          .stButton > button[kind="primary"] {{
            background-color: {C_PRIMARY} !important;
            color: #faf8f5 !important;
            border: 1px solid #152a45 !important;
          }}
          .stButton > button[kind="primary"]:hover {{
            background-color: #2a4d75 !important;
            color: #faf8f5 !important;
          }}
          .stButton > button[kind="secondary"] {{
            background-color: {C_SURFACE} !important;
            color: {C_TEXT} !important;
            border: 1px solid {C_BORDER} !important;
          }}
          .stDownloadButton > button {{
            border-radius: 6px !important;
            font-family: 'Source Sans 3', sans-serif !important;
          }}

          div[data-testid="column"] {{
            background: transparent !important;
            padding: 0 !important;
            border: none !important;
          }}
          div[data-testid="stHorizontalBlock"] {{ gap: 1rem !important; }}

          .em-card {{
            background: {C_SURFACE};
            border: 1px solid {C_BORDER};
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 1px 2px rgba(28, 25, 23, 0.04);
          }}
          .em-panel {{
            background: {C_SHARK};
            border: 1px solid {C_BORDER};
            border-radius: 8px;
            padding: 12px 14px;
            margin: 10px 0;
          }}
          .em-panel-label {{
            font-size: 0.85rem !important;
            color: {C_MUTED} !important;
            margin: 0 0 6px 0;
            font-family: 'Source Sans 3', sans-serif !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }}
          .em-panel-body {{
            color: {C_TEXT_BODY} !important;
            font-size: 17px !important;
            line-height: 1.45 !important;
            margin: 0;
            font-family: 'Source Sans 3', sans-serif !important;
          }}

          .main [class*="-em_generation_hub"] {{
            border: 1px solid {C_BORDER} !important;
            border-radius: 8px !important;
            padding: 0 !important;
            background: {C_SURFACE} !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 2px 8px rgba(28, 25, 23, 0.06);
          }}
          .main [class*="-em_generation_hub"] > div {{
            background: {C_SURFACE} !important;
            border: none !important;
            border-radius: 8px !important;
            margin: 0 !important;
            padding: 14px 16px !important;
          }}

          .stTextInput > div > div > input,
          .stTextArea > div > div > textarea,
          .stNumberInput input {{
            border-radius: 6px !important;
            background-color: {C_INPUT_BG} !important;
            color: {C_TEXT_BODY} !important;
            border: 1px solid {C_BORDER} !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 16px !important;
          }}
          .stSelectbox [data-baseweb="select"] > div {{
            border-radius: 6px !important;
            background-color: {C_INPUT_BG} !important;
            border: 1px solid {C_BORDER} !important;
            min-height: 44px !important;
          }}
          .stSelectbox [data-baseweb="select"] span {{
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 16px !important;
            color: {C_TEXT_BODY} !important;
          }}
          [data-baseweb="menu"] {{
            background-color: {C_SURFACE} !important;
            border: 1px solid {C_BORDER} !important;
          }}
          [data-baseweb="menu"] li {{
            font-family: 'Source Sans 3', sans-serif !important;
            color: {C_TEXT_BODY} !important;
          }}

          [data-testid="stExpander"] {{
            background: {C_SURFACE} !important;
            border: 1px solid {C_BORDER} !important;
            border-radius: 8px !important;
          }}
          [data-testid="stExpander"] summary {{
            color: {C_PRIMARY} !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-weight: 500 !important;
          }}

          div[data-testid="stAlert"] {{
            border-radius: 8px !important;
            border: 1px solid {C_BORDER} !important;
            background-color: {C_SURFACE} !important;
            font-family: 'Source Sans 3', sans-serif !important;
          }}
          div[data-testid="stNotification"], .stSuccess, [data-baseweb="notification"] {{
            font-family: 'Source Sans 3', sans-serif !important;
          }}

          .main [data-testid="stDataFrame"],
          .main [data-testid="stDataFrame"] > div {{
            border-radius: 8px !important;
            border: 1px solid {C_BORDER} !important;
            background: {C_SURFACE} !important;
            font-family: 'Source Sans 3', sans-serif !important;
          }}

          .ui-hero {{
            font-family: 'Crimson Pro', Georgia, serif !important;
            color: {C_HEADING} !important;
            font-size: 1.85rem !important;
            font-weight: 600 !important;
            line-height: 1.2;
            margin: 0 0 0.35rem 0;
            letter-spacing: -0.02em;
          }}
          .ui-hero-sub {{
            font-family: 'Source Sans 3', sans-serif !important;
            color: {C_MUTED} !important;
            font-size: 0.95rem !important;
            margin: 0 0 1rem 0;
            line-height: 1.45;
          }}
          .ui-active-client {{
            font-family: 'Source Sans 3', sans-serif !important;
            color: {C_TEXT} !important;
            font-size: 1.05rem !important;
            margin: 0 0 1rem 0;
            border-left: 3px solid {C_ACCENT};
            padding: 8px 12px;
            background: {C_SURFACE};
            border-radius: 0 6px 6px 0;
            border: 1px solid {C_BORDER};
            border-left: 3px solid {C_ACCENT};
          }}
          .ui-active-client .ui-accent {{ color: {C_PRIMARY} !important; font-weight: 600 !important; }}

          .em-audit-header-title {{
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: {C_MUTED} !important;
            margin: 1.5rem 0 0.2rem 0;
            font-family: 'Source Sans 3', sans-serif !important;
          }}
          .em-audit-header-name {{
            font-size: 1.35rem !important;
            color: {C_HEADING} !important;
            margin: 0 0 0.25rem 0;
            font-family: 'Crimson Pro', Georgia, serif !important;
            font-weight: 600 !important;
          }}
          .em-audit-header-sub {{
            font-size: 0.98rem !important;
            color: {C_MUTED} !important;
            margin: 0 0 0.75rem 0;
            line-height: 1.45;
            font-family: 'Source Sans 3', sans-serif !important;
          }}
          hr {{ border: none !important; border-top: 1px solid {C_BORDER} !important; margin: 1rem 0 !important; }}

          .stProgress > div > div {{
            background-color: {C_PRIMARY} !important;
          }}
          .stSpinner + div, [data-testid="stSpinner"] {{
            color: {C_PRIMARY} !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _require_gemini() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        st.error("Set GEMINI_API_KEY in your `.env` file (see `.env.example`).")
        st.stop()


def _clipboard_button(label: str, text: str) -> None:
    """Client-side copy (Midjourney / Gemini / paste into social tools).

    Note: ``streamlit.components.v1.html`` does not support a ``key=`` argument;
    each call creates a distinct iframe in document order.
    """
    payload = json.dumps(text)
    components.html(
        f"""
        <button type="button"
          style="padding:0.35rem 0.85rem;border-radius:6px;border:1px solid #cdc6b9;
                 background:#fffcf7;color:#1e3a5f;cursor:pointer;font-family:'Source Sans 3',system-ui,sans-serif;
                 font-size:15px;font-weight:500;"
          onclick="navigator.clipboard.writeText({payload}).catch(()=>{{}})">
          {html.escape(label)}
        </button>
        """,
        height=52,
    )


def _make_workflow_change_handler(post_id: int, state_key: str):
    def _go() -> None:
        db.update_post_workflow_status(post_id, st.session_state[state_key])
        st.toast("Delivery status saved.", icon="✅")
        st.rerun()

    return _go


def _overlay_to_storage(raw: object) -> str:
    if raw is None:
        return ""
    if isinstance(raw, dict):
        return json.dumps(raw, ensure_ascii=False)
    return str(raw).strip()


def _run_crew(
    client: dict,
    post_format: str,
    content_pillar: str,
    featured_brand: str,
    creative_angle: str,
    battery_featured_line: str = "Auto",
) -> dict:
    os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
    tone = (client.get("tone") or "").strip() or "Professional, clear, on-brand"
    services = (client.get("services_list") or "").strip() or "Not specified—infer carefully."
    markets = (client.get("target_markets") or "").strip() or "General local audience"
    photo_style = (client.get("photography_style") or "").strip()
    if not photo_style:
        photo_style = (
            "Photorealistic, natural lighting, authentic environment; avoid glossy, "
            "over-smoothed, generic AI stock look unless brand_context specifies otherwise."
        )
    fb = (featured_brand or FEATURED_BRAND_NONE).strip() or FEATURED_BRAND_NONE
    brand_guidelines = format_brand_guidelines_for_prompt(fb)
    brand_models = format_brand_models_for_prompt(fb)
    hooks = _creative_hook_options_for_client(client)
    hook = (creative_angle or "").strip() or random.choice(hooks)
    vm = get_vertical_mode(client)
    vrules = get_vertical_creative_rules_for_tasks(client)
    rvh = get_research_vertical_hint(client)
    bline = (battery_featured_line or "Auto").strip() or "Auto"
    inputs = {
        "company_name": client["company_name"],
        "industry": client["industry"],
        "brand_context": client["brand_context"],
        "tone": tone,
        "services_list": services,
        "target_markets": markets,
        "photography_style": photo_style,
        "post_format": post_format,
        "content_pillar": content_pillar,
        "featured_brand": fb,
        "brand_guidelines": brand_guidelines,
        "brand_models": brand_models,
        "creative_angle": hook,
        "battery_featured_line": bline,
        "vertical_mode": vm,
        "vertical_creative_rules": vrules,
        "research_vertical_hint": rvh,
    }
    result = SocialMediaCrew().crew().kickoff(inputs=inputs)
    return parse_crew_json(result.raw)


def _ensure_hub_widget_state(
    brand_options: tuple[str, ...],
    *,
    client: dict | None = None,
) -> None:
    """Initialize hub selectbox / batch keys; fix brand if options list changed."""
    brands = list(brand_options)
    hook_pool = (
        _creative_hook_options_for_client(client)
        if client is not None
        else CREATIVE_HOOK_OPTIONS
    )
    if EM_HUB_POST_FORMAT not in st.session_state:
        st.session_state[EM_HUB_POST_FORMAT] = POST_FORMAT_OPTIONS[0]
    if EM_HUB_PILLAR not in st.session_state:
        st.session_state[EM_HUB_PILLAR] = CONTENT_PILLAR_OPTIONS[0]
    if EM_HUB_BRAND not in st.session_state:
        st.session_state[EM_HUB_BRAND] = brands[0] if brands else FEATURED_BRAND_NONE
    elif st.session_state[EM_HUB_BRAND] not in brands:
        st.session_state[EM_HUB_BRAND] = FEATURED_BRAND_NONE
    if EM_HUB_HOOK not in st.session_state:
        st.session_state[EM_HUB_HOOK] = "Random"
    elif (
        st.session_state[EM_HUB_HOOK] != "Random"
        and st.session_state[EM_HUB_HOOK] not in hook_pool
    ):
        st.session_state[EM_HUB_HOOK] = "Random"
    if EM_HUB_BATCH not in st.session_state:
        st.session_state[EM_HUB_BATCH] = 1
    if client is not None:
        _b_opts = _battery_line_options_for_client(client)
        if EM_HUB_BATTERY_LINE not in st.session_state:
            st.session_state[EM_HUB_BATTERY_LINE] = _b_opts[0]
        elif st.session_state[EM_HUB_BATTERY_LINE] not in _b_opts:
            st.session_state[EM_HUB_BATTERY_LINE] = _b_opts[0]


def _crew_brands_for_client(
    client: dict,
    vault_options: list[str] | tuple[str, ...],
) -> tuple[str, ...]:
    if is_non_tyre_vertical(client):
        return (FEATURED_BRAND_NONE,)
    return tuple(vault_options)


def _gap_featured_brands_for_analysis(
    client: dict,
    vault_options: list[str] | tuple[str, ...],
) -> tuple[str, ...]:
    if is_non_tyre_vertical(client):
        return ()
    return tuple(b for b in vault_options if b != FEATURED_BRAND_NONE)


def _execute_generation_pipeline(
    client: dict,
    post_format: str,
    batch_count: int,
    content_pillar: str,
    featured_brand: str,
    hook_pick: str,
    battery_line_pick: str,
    brand_choices: tuple[str, ...],
    *,
    mixed_variety: bool = False,
) -> None:
    """CrewAI kickoff + validate JSON + save posts (same path as Authorize).

    If ``mixed_variety`` is True and batch_count > 1, each run also picks a random
    post format (Feed vs Story) for a full content mix.
    """
    n = int(batch_count)
    angle_for_run = ""
    if n <= 1 and hook_pick != "Random":
        angle_for_run = str(hook_pick)

    saved_ids: list[int] = []
    errors: list[str] = []
    bar = st.progress(0)

    def _one_payload_ok(payload: dict, run_label: str) -> tuple[str, str, str, str] | None:
        cap = payload.get("Caption")
        ip_sq = payload.get("Image_Generation_Prompt_1_1")
        ip_v = payload.get("Image_Generation_Prompt_9_16")
        legacy = payload.get("Image_Generation_Prompt")
        ov = payload.get("Suggested_Text_Overlay")
        if legacy and (not ip_sq or not ip_v):
            leg = str(legacy).strip()
            if not ip_sq:
                ip_sq = leg
            if not ip_v:
                ip_v = leg
        if not cap or not ip_sq or not ip_v or ov is None:
            errors.append(
                f"{run_label}: expected Caption, Image_Generation_Prompt_1_1, "
                f"Image_Generation_Prompt_9_16, Suggested_Text_Overlay — got keys {list(payload.keys())}"
            )
            return None
        if isinstance(ov, dict):
            if not str(ov.get("Heading", "")).strip() or not str(
                ov.get("Footer", "")
            ).strip():
                errors.append(
                    f"{run_label}: Suggested_Text_Overlay needs non-empty Heading and Footer"
                )
                return None
        else:
            errors.append(f"{run_label}: Suggested_Text_Overlay must be a JSON object")
            return None
        return (
            str(cap).strip(),
            str(ip_sq).strip(),
            str(ip_v).strip(),
            _overlay_to_storage(ov),
        )

    try:
        for i in range(n):
            run_label = f"Run {i + 1}/{n}"
            if n <= 1:
                pillar = content_pillar
                brand = featured_brand
                angle = angle_for_run
                fmt = post_format
                bline = battery_line_pick
            else:
                pillar = random.choice(CONTENT_PILLAR_OPTIONS)
                brand = random.choice(tuple(brand_choices))
                angle = ""
                fmt = (
                    random.choice(tuple(POST_FORMAT_OPTIONS))
                    if mixed_variety
                    else post_format
                )
                if is_battery_vertical(client):
                    if battery_line_pick == "Random":
                        bline = random.choice(BATTERY_FEATURED_LINE_OPTIONS)
                    else:
                        bline = battery_line_pick
                else:
                    bline = "Auto"
            bar.progress(i / max(n, 1))
            try:
                payload = _run_crew(
                    client,
                    fmt,
                    pillar,
                    brand,
                    creative_angle=angle,
                    battery_featured_line=bline,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{run_label}: CrewAI failed — {exc}")
                continue
            ok = _one_payload_ok(payload, run_label)
            if ok is None:
                with st.expander(f"{run_label} — raw JSON (invalid)", expanded=False):
                    st.json(payload)
                continue
            cap_s, ip_sq, ip_vert, ov_s = ok
            pid = db.save_post(
                int(client["id"]),
                cap_s,
                ip_sq,
                ip_vert,
                suggested_text_overlay=ov_s,
                content_pillar=pillar,
                featured_brand=brand,
                post_format=fmt,
            )
            saved_ids.append(int(pid))
        bar.progress(1.0)
    finally:
        bar.empty()

    if saved_ids:
        _sm = db.client_post_sequence_by_id(int(client["id"]))
        _nums = [_sm.get(int(x)) for x in saved_ids]
        _nums = [n for n in _nums if n is not None]
        if len(_nums) == 1:
            _id_note = f"Post #{_nums[0]}"
        elif _nums:
            _id_note = f"Posts #{_nums[0]}–{_nums[-1]}"
        else:
            _id_note = f"{len(saved_ids)} new item(s)"
        st.success(
            f"Saved **{len(saved_ids)}** asset(s) for this client ({_id_note}). "
            f"Copy captions & 1:1 / 9:16 prompts below for manual publishing."
        )
        st.toast(f"{len(saved_ids)} post(s) saved", icon="✅")
    if errors:
        st.error("Some runs failed:\n\n" + "\n\n".join(errors))
    if saved_ids:
        st.rerun()


def _ensure_active_client_id(clients: list[dict]) -> None:
    """Keep sidebar selection valid when clients are added/removed."""
    if not clients:
        return
    valid = {int(c["id"]) for c in clients}
    cur = st.session_state.get(EM_ACTIVE_CLIENT_ID)
    try:
        cur_i = int(cur) if cur is not None else -1
    except (TypeError, ValueError):
        cur_i = -1
    if cur_i not in valid:
        st.session_state[EM_ACTIVE_CLIENT_ID] = sorted(valid)[0]


def _client_by_id(clients: list[dict], client_id: int) -> dict | None:
    for c in clients:
        if int(c["id"]) == int(client_id):
            return c
    return None


def _render_sidebar_nav(clients: list[dict]) -> None:
    """Sidebar: views + one button per client (scales for many accounts)."""
    with st.sidebar:
        st.markdown(
            '<p class="ui-sidebar-title">Endpoint Media</p>',
            unsafe_allow_html=True,
        )
        st.caption("Content studio")
        st.divider()
        dash_primary = st.session_state.current_view == VIEW_DASHBOARD
        onboard_primary = st.session_state.current_view == VIEW_ONBOARD
        overlay_primary = st.session_state.current_view == VIEW_OVERLAY
        if st.button(
            "Dashboard",
            use_container_width=True,
            key="nav_generation_hub",
            type="primary" if dash_primary else "secondary",
        ):
            st.session_state.current_view = VIEW_DASHBOARD
            st.rerun()
        if st.button(
            "New client",
            use_container_width=True,
            key="nav_onboard_client",
            type="primary" if onboard_primary else "secondary",
        ):
            st.session_state.current_view = VIEW_ONBOARD
            st.rerun()
        if st.button(
            "Overlay studio",
            use_container_width=True,
            key="nav_overlay_studio",
            type="primary" if overlay_primary else "secondary",
        ):
            st.session_state.current_view = VIEW_OVERLAY
            st.rerun()

        if clients:
            st.markdown(
                '<p class="ui-sidebar-heading">Clients</p>',
                unsafe_allow_html=True,
            )
            active = int(st.session_state.get(EM_ACTIVE_CLIENT_ID, -1))
            sorted_clients = sorted(
                clients,
                key=lambda x: str(x.get("company_name", "")).lower(),
            )
            for c in sorted_clients:
                cid = int(c["id"])
                name = str(c.get("company_name", "Unknown"))
                if len(name) > 36:
                    name = name[:33] + "..."
                label = name
                if st.button(
                    label,
                    key=f"sb_client_{cid}",
                    use_container_width=True,
                    type="primary" if cid == active else "secondary",
                ):
                    st.session_state[EM_ACTIVE_CLIENT_ID] = cid
                    st.session_state.current_view = VIEW_DASHBOARD
                    st.rerun()


def _render_onboarding() -> None:
    """Distraction-free client initialization (no generation hub chrome)."""
    st.title("NEW CLIENT")
    st.caption("Add profile once — used for all CrewAI runs. Return via **Dashboard** in the sidebar.")

    row1_l, row1_r = st.columns(2, gap="large")

    with row1_l:
        st.subheader("Identity")
        st.text_input(
            "Legal or public brand name",
            key=OB_COMPANY,
            placeholder="Registered legal name or public-facing brand customers recognize",
            label_visibility="visible",
        )
        st.text_input(
            "Industry & niche",
            key=OB_INDUSTRY,
            placeholder="Primary sector and specialization (e.g., independent automotive retail, B2B SaaS for logistics)",
            label_visibility="visible",
        )

    with row1_r:
        st.subheader("Market")
        st.text_area(
            "Services, products & brands",
            key=OB_SERVICES,
            height=140,
            placeholder=(
                "List the core offerings, flagship products, and specialized services "
                "buyers should associate with this organization."
            ),
            label_visibility="visible",
        )
        st.text_area(
            "Target markets",
            key=OB_MARKETS,
            height=140,
            placeholder=(
                "Define the exact demographics, psychographics, and purchasing power of "
                "the ideal customer..."
            ),
            label_visibility="visible",
        )

    dna_col = st.columns(1)[0]
    with dna_col:
        st.subheader("Brand & voice")
        st.text_area(
            "Brand context & proof",
            key=OB_CONTEXT,
            height=220,
            placeholder=(
                "Mission, values, proof points, objections you overcome, competitors, "
                "signature proof or guarantees, and anything the AI must never imply."
            ),
            label_visibility="visible",
        )
        st.text_input(
            "Voice, tone & lexical guardrails",
            key=OB_TONE,
            placeholder=(
                "Cadence, personality, vocabulary to embrace or avoid, reading level, "
                "and regional language notes."
            ),
            label_visibility="visible",
        )
        st.text_area(
            "Photography & visual style",
            key=OB_PHOTOGRAPHY,
            height=120,
            placeholder=(
                "e.g., Gritty 90s workshop, macro close-ups, bokeh background, dirty bare hands, "
                "NO faces, NO glossy AI look."
            ),
            label_visibility="visible",
        )

    st.divider()
    st.markdown('<div class="em-init-cta">', unsafe_allow_html=True)
    if st.button("Initialize Client Profile", type="primary", use_container_width=True):
        name = (st.session_state.get(OB_COMPANY) or "").strip()
        industry = (st.session_state.get(OB_INDUSTRY) or "").strip()
        context = (st.session_state.get(OB_CONTEXT) or "").strip()
        services = (st.session_state.get(OB_SERVICES) or "").strip()
        markets = (st.session_state.get(OB_MARKETS) or "").strip()
        tone = (st.session_state.get(OB_TONE) or "").strip()
        photography = (st.session_state.get(OB_PHOTOGRAPHY) or "").strip()
        if not name or not industry or not context:
            st.error("Legal or public brand name, industry, and organizational DNA are required.")
        else:
            new_id = db.add_client(
                name,
                industry,
                context,
                tone,
                services_list=services,
                target_markets=markets,
                photography_style=photography,
            )
            st.session_state[EM_ACTIVE_CLIENT_ID] = int(new_id)
            st.toast("Client saved.")
            st.session_state.current_view = VIEW_DASHBOARD
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_dashboard_hero() -> None:
    st.markdown(
        '<p class="ui-hero">Endpoint Media — Content console</p>'
        '<p class="ui-hero-sub">Select a client in the sidebar, generate posts, copy captions & prompts, '
        "and track delivery.</p>",
        unsafe_allow_html=True,
    )


def _build_post_delivery_zip(post: dict) -> tuple[bytes, str]:
    """ZIP: caption.txt, meta.json, square/vertical files from disk."""
    meta = {
        "post_id": int(post["id"]),
        "client": post.get("client_company_name"),
        "caption_excerpt": (str(post.get("caption") or ""))[:200],
        "publisher_status": post.get("publisher_status"),
        "scheduled_for": post.get("scheduled_for"),
    }
    buf = io.BytesIO()
    cid = int(post["client_id"])
    pid = int(post["id"])
    arc_base = f"post_{cid}_{pid}"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{arc_base}/caption.txt", str(post.get("caption") or ""))
        zf.writestr(
            f"{arc_base}/meta.json",
            json.dumps(meta, indent=2, ensure_ascii=False),
        )
        sq = db.resolve_asset_path(str(post.get("image_square_path") or ""))
        vt = db.resolve_asset_path(str(post.get("image_vertical_path") or ""))
        if sq.is_file():
            zf.write(sq, arcname=f"{arc_base}/square{sq.suffix.lower()}")
        if vt.is_file():
            zf.write(vt, arcname=f"{arc_base}/vertical{vt.suffix.lower()}")
    name = f"endpoint_post_{cid}_{pid}.zip"
    return buf.getvalue(), name


def _render_publisher_queue() -> None:
    """Private link: external Facebook publisher — no admin login."""
    st.title("Publisher queue")
    st.caption(
        "Ready posts (QC approved). Download assets, copy captions, then schedule or mark posted "
        "on your side."
    )
    client_ids = db.get_publisher_queue_client_ids()
    if not client_ids:
        st.warning(
            "No clients match **PUBLISHER_QUEUE_CLIENTS** in `.env`. "
            "Add comma-separated name fragments (e.g. `alberton tyre clinic,alberton battery mart`)."
        )
        return
    posts = db.get_posts_for_publisher(client_ids)
    if not posts:
        st.info("No posts are **Ready for Publisher** yet. The studio marks them ready after final images upload.")
        return
    st.success(f"{len(posts)} post(s) in queue.", icon="📋")
    _by_client: dict[int, list[dict]] = {}
    for p in posts:
        cid = int(p["client_id"])
        _by_client.setdefault(cid, []).append(p)
    for cid in sorted(_by_client.keys()):
        cname = (_by_client[cid][0].get("client_company_name") or f"Client #{cid}").strip()
        st.markdown(f"### {html.escape(cname)}")
        for row in _by_client[cid]:
            pid = int(row["id"])
            with st.expander(
                f"Post #{pid} · {str(row.get('created_at') or row.get('generated_date') or '')[:19]}",
                expanded=False,
            ):
                st.markdown(
                    f'<p style="color:{C_GRAY};font-size:0.9rem;">'
                    f"{html.escape(str(row.get('client_company_name') or ''))}</p>",
                    unsafe_allow_html=True,
                )
                st.text_area(
                    "Caption",
                    value=str(row.get("caption") or ""),
                    height=min(200, 60 + len(str(row.get('caption') or "")) // 5),
                    key=f"pub_cap_ro_{pid}",
                    disabled=True,
                )
                _clipboard_button("Copy caption", str(row.get("caption") or ""))
                img_row = st.columns(2)
                sq = db.resolve_asset_path(str(row.get("image_square_path") or ""))
                vt = db.resolve_asset_path(str(row.get("image_vertical_path") or ""))
                with img_row[0]:
                    st.caption("Square (1:1)")
                    if sq.is_file():
                        st.image(str(sq))
                    else:
                        st.warning("Missing square file on disk.")
                with img_row[1]:
                    st.caption("Vertical (9:16)")
                    if vt.is_file():
                        st.image(str(vt))
                    else:
                        st.warning("Missing vertical file on disk.")
                zdata, zname = _build_post_delivery_zip(row)
                st.download_button(
                    label="Download ZIP (caption + images + meta)",
                    data=zdata,
                    file_name=zname,
                    mime="application/zip",
                    key=f"dl_zip_{pid}",
                )
                _ps = str(row.get("publisher_status") or db.PUBLISHER_UNSCHEDULED)
                if _ps not in db.PUBLISHER_STATUSES:
                    _ps = db.PUBLISHER_UNSCHEDULED
                try:
                    _idx = list(db.PUBLISHER_STATUSES).index(_ps)
                except ValueError:
                    _idx = 0
                with st.form(f"pub_save_{pid}"):
                    st.selectbox(
                        "Publisher status",
                        options=list(db.PUBLISHER_STATUSES),
                        index=_idx,
                        key=f"pub_st_{pid}",
                    )
                    st.text_input(
                        "Scheduled for (free text, e.g. ISO date)",
                        value=str(row.get("scheduled_for") or ""),
                        key=f"pub_sched_{pid}",
                    )
                    st.text_area(
                        "Notes",
                        value=str(row.get("publisher_notes") or ""),
                        key=f"pub_notes_{pid}",
                    )
                    submitted = st.form_submit_button("Save publisher fields")
                    if submitted:
                        sel = st.session_state.get(f"pub_st_{pid}")
                        sched = st.session_state.get(f"pub_sched_{pid}", "")
                        notes = st.session_state.get(f"pub_notes_{pid}", "")
                        mark_now = sel == db.PUBLISHER_POSTED
                        db.update_post_publisher_fields(
                            pid,
                            publisher_status=str(sel),
                            scheduled_for=str(sched),
                            publisher_notes=str(notes),
                            set_published_now=mark_now,
                        )
                        for _k in (
                            f"pub_st_{pid}",
                            f"pub_sched_{pid}",
                            f"pub_notes_{pid}",
                        ):
                            st.session_state.pop(_k, None)
                        st.success("Saved.")
                        st.rerun()


def _render_overlay_studio(clients: list[dict]) -> None:
    """Titan-style HTML exporter (html2canvas) — matches your prototype layout."""
    _ = clients  # reserved if we later inject DB-driven presets into the iframe
    st.title("Overlay Studio")
    st.caption(
        "Titan Ad Exporter: dark panel, centered brand header, optional sub-text, frosted "
        "glass footer — export high-res JPEG via html2canvas (same as your HTML)."
    )
    if not _TITAN_EXPORTER_HTML.is_file():
        st.error(
            f"Missing exporter file: `{_TITAN_EXPORTER_HTML}`. "
            "Restore `static/titan_ad_exporter.html` in the project."
        )
        return
    html_src = _TITAN_EXPORTER_HTML.read_text(encoding="utf-8")
    components.html(html_src, height=1180, scrolling=True)
    st.info(
        f"**Standalone:** open `{_TITAN_EXPORTER_HTML}` directly in Chrome/Edge if the embedded "
        "view blocks the CDN script (rare). "
        "Presets: Alberton Tyre Clinic, Alberton Battery Mart, Miwesu Fire Wood."
    )


def main() -> None:
    st.set_page_config(
        page_title="Endpoint Media — Content",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_classical_theme()
    db.init_db()

    _qp_view = st.query_params.get("view")
    if _qp_view == "publisher":
        _key = (st.query_params.get("key") or "").strip()
        _expected = os.getenv("PUBLISHER_SHARED_KEY", "").strip()
        if not _expected or _key != _expected:
            st.error("Invalid or missing publisher link. Ask the studio for the current URL.")
            st.stop()
        _render_publisher_queue()
        return

    if "current_view" not in st.session_state:
        st.session_state.current_view = VIEW_DASHBOARD

    clients = db.get_all_clients()
    if clients:
        _ensure_active_client_id(clients)
    _render_sidebar_nav(clients)

    if st.session_state.current_view == VIEW_ONBOARD:
        _render_onboarding()
        return
    if st.session_state.current_view == VIEW_OVERLAY:
        _render_overlay_studio(clients)
        return

    _render_dashboard_hero()

    if not clients:
        st.markdown(
            f'<div class="em-card"><p style="color:{C_ATHENS};margin:0;">'
            f"No clients yet. In the sidebar, click "
            f'<strong style="color:{C_TEXT};">{VIEW_ONBOARD}</strong> to add one.</p></div>',
            unsafe_allow_html=True,
        )
        return

    _require_gemini()

    brand_choices = featured_brand_select_options()

    _cid = int(st.session_state[EM_ACTIVE_CLIENT_ID])
    client = _client_by_id(clients, _cid)
    if client is None:
        _ensure_active_client_id(clients)
        _cid = int(st.session_state[EM_ACTIVE_CLIENT_ID])
        client = _client_by_id(clients, _cid)
    if client is None:
        st.error("Could not resolve active client. Pick one in the sidebar.")
        st.stop()

    _cn_disp = html.escape(str(client["company_name"]))
    st.markdown(
        f'<p class="ui-active-client">Active client: '
        f'<span class="ui-accent">{_cn_disp}</span> &nbsp;&middot;&nbsp; profile #{_cid}</p>',
        unsafe_allow_html=True,
    )
    _ensure_hub_widget_state(
        _crew_brands_for_client(client, brand_choices),
        client=client,
    )

    st.markdown("**Content gaps** (last 30 days)")
    _alerts = db.get_content_gap_analysis(
        _cid,
        content_pillars=CONTENT_PILLAR_OPTIONS,
        featured_brands=_gap_featured_brands_for_analysis(client, brand_choices),
        brand_none_label=FEATURED_BRAND_NONE,
    )
    if not _alerts:
        st.success(
            "No major content gaps in the last 30 days for this client — stay consistent.",
            icon="✅",
        )
    else:
        for _i, _alert in enumerate(_alerts):
            _ac, _bc = st.columns((4, 2))
            with _ac:
                if _alert.get("severity") == "warning":
                    st.warning(_alert["message"])
                else:
                    st.info(_alert["message"])
            with _bc:
                if st.button(
                    "Generate Post to Fill Gap",
                    key=f"gap_fill_{_cid}_{_i}",
                    use_container_width=True,
                ):
                    _pf = _alert.get("pillar")
                    _bf = _alert.get("brand")
                    _pillar_go = (
                        _pf
                        if _pf and _pf in CONTENT_PILLAR_OPTIONS
                        else st.session_state[EM_HUB_PILLAR]
                    )
                    _eff = _crew_brands_for_client(client, brand_choices)
                    if _bf and _bf in _eff:
                        _brand_go = _bf
                    else:
                        _brand_go = st.session_state[EM_HUB_BRAND]
                    st.session_state[EM_HUB_BATCH] = 1
                    st.session_state[EM_HUB_PILLAR] = _pillar_go
                    st.session_state[EM_HUB_BRAND] = _brand_go
                    _fmt_go = st.session_state.get(
                        EM_HUB_POST_FORMAT, POST_FORMAT_OPTIONS[0]
                    )
                    _hook_go = st.session_state.get(EM_HUB_HOOK, "Random")
                    _bline_go = st.session_state.get(EM_HUB_BATTERY_LINE, "Auto")
                    st.toast("Filling gap — running CrewAI…", icon="🧩")
                    _execute_generation_pipeline(
                        client,
                        _fmt_go,
                        1,
                        _pillar_go,
                        _brand_go,
                        _hook_go,
                        _bline_go,
                        _crew_brands_for_client(client, brand_choices),
                    )

    with st.container(border=True, key="em_generation_hub", gap="medium"):
        st.markdown("#### Generate")

        # Auto-Pilot must mutate hub keys before selectboxes/inputs with those keys run.
        if st.session_state.pop(EM_PENDING_AUTOPILOT, False):
            st.session_state[EM_HUB_POST_FORMAT] = random.choice(tuple(POST_FORMAT_OPTIONS))
            st.session_state[EM_HUB_PILLAR] = random.choice(tuple(CONTENT_PILLAR_OPTIONS))
            st.session_state[EM_HUB_BRAND] = random.choice(
                _crew_brands_for_client(client, brand_choices)
            )
            st.session_state[EM_HUB_HOOK] = random.choice(
                tuple(_creative_hook_options_for_client(client))
            )
            if is_battery_vertical(client):
                st.session_state[EM_HUB_BATTERY_LINE] = random.choice(
                    ("Random",) + BATTERY_FEATURED_LINE_OPTIONS
                )
            else:
                st.session_state[EM_HUB_BATTERY_LINE] = "Auto"
            st.session_state[EM_HUB_BATCH] = 1
            _ap_pf = st.session_state[EM_HUB_POST_FORMAT]
            _ap_pil = st.session_state[EM_HUB_PILLAR]
            _ap_br = st.session_state[EM_HUB_BRAND]
            _ap_hk = st.session_state[EM_HUB_HOOK]
            _ap_bl = st.session_state.get(EM_HUB_BATTERY_LINE, "Auto")
            _ap_brand_toast = (
                "no co-brand (None)"
                if _ap_br == FEATURED_BRAND_NONE
                else str(_ap_br)
            )
            st.toast(
                f"Auto-Pilot engaged: Generating a {_ap_pf} about {_ap_pil} featuring {_ap_brand_toast}!",
                icon="🎲",
            )
            _execute_generation_pipeline(
                client,
                _ap_pf,
                1,
                _ap_pil,
                _ap_br,
                _ap_hk,
                _ap_bl,
                _crew_brands_for_client(client, brand_choices),
            )

        _cn = html.escape(str(client["company_name"]))
        _ind = html.escape(str(client["industry"]))
        st.markdown(
            f'<div class="em-card" style="margin-top:8px;">'
            f'<p style="color:{C_WHITE};font-size:1.25rem;font-weight:600;margin:0 0 4px 0;">{_cn}</p>'
            f'<p style="color:{C_GRAY};margin:0 0 12px 0;">{_ind}</p></div>',
            unsafe_allow_html=True,
        )
        if is_firewood_vertical(client):
            _mix_intro = (
                f"<p style='color:{C_ATHENS};font-size:1.02rem;margin:0 0 16px 0;'>"
                f"Click once to create <strong style='color:{C_WHITE};'>{MIXED_PACK_POST_COUNT} posts</strong> "
                f"with a random mix of pillars (service, education, promo, authority), "
                f"<strong style='color:{C_WHITE};'>Feed + Story</strong> formats, and creative hooks—"
                f"delivery, braai/coals, product hero, did-you-know, and promo angles driven by your brief "
                f"(wood lines, moisture/dry story, Gauteng delivery, WhatsApp orders). "
                f"<strong style='color:{C_WHITE};'>No tyre co-brands</strong> for this client.</p>"
            )
        elif is_battery_vertical(client):
            _mix_intro = (
                f"<p style='color:{C_ATHENS};font-size:1.02rem;margin:0 0 16px 0;'>"
                f"Click once to create <strong style='color:{C_WHITE};'>{MIXED_PACK_POST_COUNT} posts</strong> "
                f"with a random mix of pillars (service, education, promo, authority), "
                f"<strong style='color:{C_WHITE};'>Feed + Story</strong> formats, and hooks—"
                f"battery diagnostics, mobile callouts, fitment, and backup power angles from your brief. "
                f"<strong style='color:{C_WHITE};'>No tyre co-brands</strong> for this client.</p>"
            )
        else:
            _mix_intro = (
                f"<p style='color:{C_ATHENS};font-size:1.02rem;margin:0 0 16px 0;'>"
                f"Click once to create <strong style='color:{C_WHITE};'>{MIXED_PACK_POST_COUNT} posts</strong> "
                f"with a random mix of pillars (service, education, promo, authority), "
                f"<strong style='color:{C_WHITE};'>Feed + Story</strong> formats, "
                f"tyre co-brands (or None), and hooks—workshop, product ads, did-you-knows, and more.</p>"
            )
        st.markdown(_mix_intro, unsafe_allow_html=True)

        _pid = int(client["id"])
        _ph_key = f"photo_style_edit_{_pid}"
        if _ph_key not in st.session_state:
            st.session_state[_ph_key] = str(client.get("photography_style") or "")
        with st.expander("Photography & visual style (applies to all generations)", expanded=False):
            st.caption(
                "Feeds CrewAI image prompts. "
                + (
                    "Match real sets—product, delivery, braai, hearth; anti-glossy, documentary realism."
                    if is_firewood_vertical(client)
                    else (
                        "Match real battery scenes—engine bay fitment, diagnostics, callouts; no phones/screens."
                        if is_battery_vertical(client)
                        else "Match your real workshop—anti-glossy, documentary realism."
                    )
                )
            )
            st.text_area(
                "Photography & visual style",
                height=260,
                key=_ph_key,
                placeholder=(
                    "e.g., Hardware Noir product hero; bronze rim light on splits; shallow DOF; "
                    "alternate flames/coals, delivery, macro bark—no bag every post; NO glossy CGI."
                    if is_firewood_vertical(client)
                    else (
                        "e.g., Battery fitment bay + under-bonnet closeups; Midtronics tester in frame; "
                        "mobile callout van context; no phones/app UI; NO glossy CGI."
                        if is_battery_vertical(client)
                        else (
                            "e.g., Documentary-style SA fitment centre; black coin-mat floors, orange lifts, "
                            "fluorescent + daylight from roll-up door; DSLR 50mm; NO faces, NO glossy CGI."
                        )
                    )
                ),
                label_visibility="collapsed",
            )
            if st.button("Save photography style", key=f"save_photo_style_{_pid}"):
                db.update_client(_pid, photography_style=str(st.session_state.get(_ph_key) or ""))
                st.session_state.pop(_ph_key, None)
                st.success("Photography style saved.")
                st.rerun()

        st.caption(
            f"⏱ {MIXED_PACK_POST_COUNT} sequential AI runs — usually about a minute or two total. "
            "Progress bar updates below; failed runs are listed without stopping the batch."
        )
        if st.button(
            f"Generate {MIXED_PACK_POST_COUNT} mixed posts",
            type="primary",
            use_container_width=True,
            key="em_generate_mixed_pack",
        ):
            _execute_generation_pipeline(
                client,
                POST_FORMAT_OPTIONS[0],
                MIXED_PACK_POST_COUNT,
                CONTENT_PILLAR_OPTIONS[0],
                FEATURED_BRAND_NONE,
                "Random",
                "Random" if is_battery_vertical(client) else "Auto",
                _crew_brands_for_client(client, brand_choices),
                mixed_variety=True,
            )

        with st.expander("Manual generation — one post, custom batch, or Auto-Pilot", expanded=False):
            col_format, col_batch = st.columns(2, gap="large")

            with col_format:
                st.markdown(
                    f'<p style="color:{C_GRAY};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Post format</p>',
                    unsafe_allow_html=True,
                )
                post_format = st.selectbox(
                    "Post format",
                    options=POST_FORMAT_OPTIONS,
                    label_visibility="collapsed",
                    key=EM_HUB_POST_FORMAT,
                )

            with col_batch:
                st.markdown(
                    f'<p style="color:{C_GRAY};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Batch size</p>',
                    unsafe_allow_html=True,
                )
                batch_count = st.number_input(
                    "How many posts to generate",
                    min_value=1,
                    max_value=30,
                    step=1,
                    help="Batch mode randomizes pillar, tyre brand, and hook each run. "
                    "Enable “Randomize Feed vs Story” below for the same variety as the main button.",
                    label_visibility="collapsed",
                    key=EM_HUB_BATCH,
                )

            _mix_fmt_key = "em_manual_mixed_format"
            if int(batch_count) > 1:
                st.checkbox(
                    "Randomize Feed vs Story format on each post (recommended for variety packs)",
                    key=_mix_fmt_key,
                    value=True,
                )

            if int(batch_count) <= 1:
                col_pillar, col_brand, col_hook = st.columns(3, gap="large")
                with col_pillar:
                    st.markdown(
                        f'<p style="color:{C_GRAY};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Content pillar</p>',
                        unsafe_allow_html=True,
                    )
                    content_pillar = st.selectbox(
                        "Content pillar",
                        options=CONTENT_PILLAR_OPTIONS,
                        label_visibility="collapsed",
                        key=EM_HUB_PILLAR,
                    )
                with col_brand:
                    st.markdown(
                        f'<p style="color:{C_GRAY};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Featured brand</p>',
                        unsafe_allow_html=True,
                    )
                    featured_brand = st.selectbox(
                        "Featured brand",
                        options=list(_crew_brands_for_client(client, brand_choices)),
                        label_visibility="collapsed",
                        key=EM_HUB_BRAND,
                    )
                with col_hook:
                    st.markdown(
                        f'<p style="color:{C_GRAY};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Creative hook</p>',
                        unsafe_allow_html=True,
                    )
                    hook_pick = st.selectbox(
                        "Creative hook",
                        options=["Random"] + list(_creative_hook_options_for_client(client)),
                        label_visibility="collapsed",
                        key=EM_HUB_HOOK,
                    )
                if is_battery_vertical(client):
                    st.markdown(
                        f'<p style="color:{C_GRAY};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:10px 0 8px 0;">Battery featured line</p>',
                        unsafe_allow_html=True,
                    )
                    battery_line_pick = st.selectbox(
                        "Battery featured line",
                        options=list(_battery_line_options_for_client(client)),
                        label_visibility="collapsed",
                        key=EM_HUB_BATTERY_LINE,
                    )
                else:
                    battery_line_pick = "Auto"
            else:
                _batch_brand_note = (
                    "**co-brand stays off** (non-tyre vertical)"
                    if is_non_tyre_vertical(client)
                    else "**featured tyre brand** (including None)"
                )
                st.info(
                    f"**Batch ×{int(batch_count)}** — each run randomizes **content pillar**, "
                    f"{_batch_brand_note}, and **creative hook**. "
                    "Use the checkbox above to also randomize **Feed vs Story** per post."
                )
                if is_battery_vertical(client):
                    battery_line_pick = st.selectbox(
                        "Battery featured line in batch",
                        options=["Random"] + list(_battery_line_options_for_client(client)),
                        help="Choose a fixed battery line for all runs, or Random.",
                        key=EM_HUB_BATTERY_LINE,
                    )
                else:
                    battery_line_pick = "Auto"
                content_pillar = CONTENT_PILLAR_OPTIONS[0]
                featured_brand = FEATURED_BRAND_NONE
                hook_pick = "Random"

            with st.expander("Client brief", expanded=False):
                st.markdown(
                    f'<p style="color:{C_GRAY};"><strong style="color:{C_WHITE};">Tone</strong> · '
                    f'{html.escape(str(client.get("tone") or "—"))}</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p style="color:{C_GRAY};"><strong style="color:{C_WHITE};">Services</strong> · '
                    f'{html.escape(str(client.get("services_list") or "—"))}</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p style="color:{C_GRAY};"><strong style="color:{C_WHITE};">Markets</strong> · '
                    f'{html.escape(str(client.get("target_markets") or "—"))}</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p style="color:{C_GRAY};"><strong style="color:{C_WHITE};">Photography & visual</strong> · '
                    f'{html.escape(str(client.get("photography_style") or "—"))}</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p style="color:{C_ATHENS};">{html.escape(str(client["brand_context"]))}</p>',
                    unsafe_allow_html=True,
                )

            _fmt = html.escape(str(post_format))
            _pil = html.escape(str(content_pillar))
            _fb = html.escape(str(featured_brand))
            _co = (
                f" Co-brand vault: <strong>{_fb}</strong>."
                if featured_brand != FEATURED_BRAND_NONE
                else ""
            )
            if int(batch_count) <= 1:
                _hk = (
                    "Random hook"
                    if hook_pick == "Random"
                    else html.escape(str(hook_pick)[:120])
                )
                _batch_line = (
                    f"Pillar: <strong>{_pil}</strong>. Creative hook: <strong>{_hk}</strong>. "
                    f"You copy caption & prompts; images are created manually."
                )
            else:
                _vf = (
                    "Feed + Story mixed each run."
                    if st.session_state.get(_mix_fmt_key, True)
                    else "Single format (left) for all runs."
                )
                _batch_line = (
                    f"<strong>{int(batch_count)}</strong> runs — randomized pillar, brand, hook. {_vf}"
                )
            st.markdown(
                f'<div class="em-panel" role="region" aria-label="Plan summary">'
                f'<p class="em-panel-label">Plan summary</p>'
                f'<p class="em-panel-body"><strong>What runs:</strong> Research on <strong>{_cn}</strong> '
                f"(<strong>{_ind}</strong>), then one creative pass → caption + 1:1 & 9:16 image prompts + overlay JSON."
                f"{_co if int(batch_count) <= 1 else ''}</p>"
                f'<p class="em-panel-body" style="margin-top:0.5rem;">{_batch_line}</p>'
                f"</div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<div style='height:8px;' aria-hidden='true'></div>",
                unsafe_allow_html=True,
            )
            btn_auth, btn_auto = st.columns(2, gap="medium")
            with btn_auth:
                if st.button(
                    "Run generation",
                    type="primary",
                    use_container_width=True,
                    key="em_authorize_execute",
                ):
                    _manual_mixed = (
                        int(batch_count) > 1 and st.session_state.get(_mix_fmt_key, True)
                    )
                    _execute_generation_pipeline(
                        client,
                        post_format,
                        int(batch_count),
                        content_pillar,
                        featured_brand,
                        hook_pick,
                        battery_line_pick,
                        _crew_brands_for_client(client, brand_choices),
                        mixed_variety=_manual_mixed,
                    )
            with btn_auto:
                if st.button(
                    "Auto-Pilot (random settings)",
                    type="secondary",
                    use_container_width=True,
                    key="em_autopilot_surprise",
                    help="Random format, pillar, brand & hook—then runs the same CrewAI save pipeline.",
                ):
                    st.session_state[EM_PENDING_AUTOPILOT] = True
                    st.rerun()

    st.markdown(
        f'<p class="em-audit-header-title" style="margin-top:2.5rem;">Post library</p>'
        f'<p class="em-audit-header-name">Asset delivery &amp; delivery tracking</p>'
        f'<p class="em-audit-header-sub">Copy captions and image prompts into Midjourney, Gemini, or your '
        f"design stack. Update status as you send work to clients and when it goes live.</p>",
        unsafe_allow_html=True,
    )
    posts = db.get_posts_for_client(int(client["id"]))
    if not posts:
        st.markdown(
            f'<div class="em-card"><p style="color:{C_GRAY};margin:0;">'
            f"No generated assets yet for this client.</p></div>",
            unsafe_allow_html=True,
        )
        return

    _seq_map = db.client_post_sequence_by_id(int(client["id"]))
    _summary_rows = []
    for _p in posts:
        _ts = (_p.get("created_at") or _p.get("generated_date") or "")[:19]
        _pid_i = int(_p["id"])
        _summary_rows.append(
            {
                "Post #": _seq_map.get(_pid_i, "?"),
                "created": _ts,
                "pillar": (_p.get("content_pillar") or "—")[:40],
                "brand": (_p.get("featured_brand") or "—")[:24],
                "format": (_p.get("post_format") or "—")[:32],
                "delivery": _p.get("workflow_status") or "Draft",
                "QC": (_p.get("qc_status") or db.QC_STATUS_DRAFT)[:24],
            }
        )
    st.dataframe(
        pd.DataFrame(_summary_rows),
        use_container_width=True,
        hide_index=True,
    )

    for row in posts:
        _pid = int(row["id"])
        _post_num = _seq_map.get(_pid, "?")
        _ts_disp = html.escape(
            str((row.get("created_at") or row.get("generated_date") or ""))[:19]
        )
        _wf = row.get("workflow_status") or "Draft"
        if _wf not in db.WORKFLOW_STATUSES:
            _wf = "Draft"
        _wk = f"post_workflow_{int(client['id'])}_{_pid}"
        if _wk not in st.session_state:
            st.session_state[_wk] = _wf

        st.markdown(
            f'<div class="em-card" style="margin-top:1.25rem;padding:1rem 1.1rem;">'
            f'<p style="color:{C_GRAY};font-size:0.85rem;margin:0 0 4px 0;">'
            f"Post #{_post_num} · {_ts_disp}</p>"
            f'<p style="color:{C_WHITE};font-weight:600;margin:0 0 12px 0;">Suggested caption</p></div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Suggested caption",
            value=str(row["caption"]),
            height=min(220, 80 + len(str(row["caption"])) // 4),
            key=f"asset_cap_{_cid}_{_pid}",
            label_visibility="collapsed",
            disabled=True,
        )
        _clipboard_button("Copy caption", str(row["caption"]))

        _img_sq = (row.get("image_prompt_square") or "").strip() or str(row.get("image_prompt") or "")
        _img_916 = (row.get("image_prompt_vertical") or "").strip() or str(row.get("image_prompt") or "")
        st.markdown(
            f'<p style="color:{C_WHITE};font-weight:600;margin-top:1rem;">'
            f"AI image prompts (same idea — two crops)</p>"
            f'<p style="color:{C_GRAY};font-size:0.88rem;margin:0 0 8px 0;">'
            f"1:1 = feed / square · 9:16 = Stories / Reels — paste into Midjourney / Gemini / Imagen.</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="color:{C_GRAY};font-size:0.82rem;margin:0 0 4px 0;">1:1 — feed (square)</p>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Image prompt 1:1",
            value=str(_img_sq),
            height=min(280, 100 + len(str(_img_sq)) // 4),
            key=f"asset_img_11_{_cid}_{_pid}",
            label_visibility="collapsed",
            disabled=True,
        )
        _clipboard_button("Copy 1:1 prompt", str(_img_sq))
        st.markdown(
            f'<p style="color:{C_GRAY};font-size:0.82rem;margin:0.75rem 0 4px 0;">9:16 — vertical (Stories)</p>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Image prompt 9:16",
            value=str(_img_916),
            height=min(280, 100 + len(str(_img_916)) // 4),
            key=f"asset_img_916_{_cid}_{_pid}",
            label_visibility="collapsed",
            disabled=True,
        )
        _clipboard_button("Copy 9:16 prompt", str(_img_916))

        st.markdown(
            f'<p style="color:{C_WHITE};font-weight:600;margin-top:1.25rem;">'
            f"Final images (manual export)</p>"
            f'<p style="color:{C_GRAY};font-size:0.88rem;margin:0 0 8px 0;">'
            f"Upload square (1:1) and vertical (9:16) files after Titan / design export. "
            f"Mark <strong>Ready for Publisher</strong> when QC passes — your publisher link only shows ready posts.</p>",
            unsafe_allow_html=True,
        )
        _qc = str(row.get("qc_status") or db.QC_STATUS_DRAFT)
        if _qc not in db.QC_STATUSES:
            _qc = db.QC_STATUS_DRAFT
        st.caption(f"QC status: **{_qc}**")
        _sq_disk = db.resolve_asset_path(str(row.get("image_square_path") or ""))
        _vt_disk = db.resolve_asset_path(str(row.get("image_vertical_path") or ""))
        _prev = st.columns(2)
        with _prev[0]:
            if _sq_disk.is_file():
                st.image(str(_sq_disk), caption="Square on disk")
            else:
                st.caption("No square file yet.")
        with _prev[1]:
            if _vt_disk.is_file():
                st.image(str(_vt_disk), caption="Vertical on disk")
            else:
                st.caption("No vertical file yet.")
        _u1, _u2 = st.columns(2)
        with _u1:
            up_sq = st.file_uploader(
                "Square file",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"fu_sq_{_cid}_{_pid}",
            )
        with _u2:
            up_vt = st.file_uploader(
                "Vertical file",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"fu_vt_{_cid}_{_pid}",
            )
        _save_col, _rdy_col, _rev_col = st.columns(3)
        with _save_col:
            if st.button(
                "Save final images",
                key=f"save_final_{_cid}_{_pid}",
                use_container_width=True,
            ):
                if up_sq is None or up_vt is None:
                    st.error("Upload both square and vertical files before saving.")
                else:
                    _suf_sq = Path(up_sq.name).suffix.lower() or ".png"
                    _suf_vt = Path(up_vt.name).suffix.lower() or ".png"
                    db.save_post_final_assets(
                        int(client["id"]),
                        _pid,
                        up_sq.getvalue(),
                        up_vt.getvalue(),
                        square_suffix=_suf_sq,
                        vertical_suffix=_suf_vt,
                    )
                    st.success("Final images saved.")
                    st.rerun()
        _has_both = _sq_disk.is_file() and _vt_disk.is_file()
        with _rdy_col:
            if st.button(
                "Mark ready for publisher",
                key=f"qc_ready_{_cid}_{_pid}",
                use_container_width=True,
                disabled=not _has_both or _qc == db.QC_STATUS_READY,
            ):
                db.set_post_qc_ready(_pid)
                st.success("Marked ready — visible on publisher link.")
                st.rerun()
        with _rev_col:
            if st.button(
                "Revert QC to draft",
                key=f"qc_draft_{_cid}_{_pid}",
                use_container_width=True,
                disabled=_qc == db.QC_STATUS_DRAFT,
            ):
                db.set_post_qc_draft(_pid)
                st.info("Reverted to draft (hidden from publisher queue).")
                st.rerun()

        overlay_raw = row.get("suggested_text_overlay") or ""
        if overlay_raw:
            with st.expander("Suggested text overlay (JSON)", expanded=False):
                try:
                    st.json(json.loads(overlay_raw))
                except json.JSONDecodeError:
                    st.text(overlay_raw)

        _meta = []
        if (row.get("content_pillar") or "").strip():
            _meta.append(f"Pillar · **{html.escape(row['content_pillar'])}**")
        if (row.get("featured_brand") or "").strip():
            _meta.append(f"Brand · **{html.escape(row['featured_brand'])}**")
        if (row.get("post_format") or "").strip():
            _meta.append(f"Format · **{html.escape(row['post_format'])}**")
        if _meta:
            st.markdown(
                f"<p style='color:{C_GRAY};font-size:0.9rem;margin-top:12px;'>"
                + " &nbsp;|&nbsp; ".join(_meta)
                + "</p>",
                unsafe_allow_html=True,
            )

        st.selectbox(
            "Delivery status",
            options=list(db.WORKFLOW_STATUSES),
            key=_wk,
            on_change=_make_workflow_change_handler(_pid, _wk),
        )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
