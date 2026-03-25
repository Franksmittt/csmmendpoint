"""Endpoint Media CRM — Streamlit dashboard (CrewAI + SQLite)."""

import calendar
import hashlib
import html
import io
import json
import logging
import os
import random
import tempfile
from datetime import date, datetime, timedelta, timezone
import sys
import zipfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image as PILImage
import streamlit.components.v1 as components
from dotenv import load_dotenv

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

load_dotenv(_SRC.parent / ".env")


def _hydrate_env_from_streamlit_secrets() -> None:
    """Streamlit Community Cloud stores keys in st.secrets; CrewAI reads os.environ."""
    try:
        sec = st.secrets
    except Exception:
        return
    for key in (
        "GEMINI_API_KEY",
        "MODEL",
        "PUBLISHER_SHARED_KEY",
        "PUBLISHER_QUEUE_CLIENTS",
        "PUBLIC_APP_URL",
    ):
        if key in sec and not (os.getenv(key) or "").strip():
            val = sec[key]
            if val is not None and str(val).strip():
                os.environ[key] = str(val).strip()


import analytics
import asset_pipeline
import content_calendar
import engagement_learner
import roles as role_ctx
import video_prompts
import bulk_actions
import database as db
import image_generation
import overlay_pil
from crew import (
    CaptionOnlyCrew,
    CriticRefinementCrew,
    SocialMediaCrew,
    VideoPromptOnlyCrew,
    inject_engagement_insights,
)
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
    is_offroad_vertical,
)
from json_utils import parse_crew_json

logger = logging.getLogger(__name__)

# Design tokens — Bento–Halo (Athens gray field, white squircle cards, navy/bronze accents)
C_BG = "#F5F5F7"  # Apple Athens Gray — reduced eye strain
C_SURFACE = "#FFFFFF"  # pure white cards
C_TEXT = "#1d1d1f"
C_TEXT_BODY = "#424245"
C_MUTED = "#6e6e73"
C_BORDER = "#CDC6B9"  # subtle warm hairline (spec)
C_INPUT_BG = "#FAFAFA"
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
C_SHARK = "#F5F5F7"  # nested panels on white
C_CONFIDENCE = C_SUCCESS
# Motion (Samsung One UI–style ease)
C_EASE_PRODUCT = "cubic-bezier(0.22, 0.25, 0.00, 1.0)"


def _theme_inline() -> tuple[str, str, str]:
    """(emphasis, muted, body) hex for inline HTML — readable in light and dark mode."""
    if bool(st.session_state.get(EM_DARK_MODE, False)):
        return "#f5f5f7", "#a1a1a6", "#d1d1d6"
    return C_WHITE, C_GRAY, C_TEXT


VIEW_DASHBOARD = "Dashboard"
VIEW_ONBOARD = "New client"
VIEW_OVERLAY = "Overlay studio"
VIEW_ANALYTICS = "Analytics"
VIEW_CONTENT_CALENDAR = "Content Calendar"

# Titan-style HTML exporter (html2canvas) — embedded in Overlay studio.
_TITAN_EXPORTER_HTML = Path(__file__).resolve().parent.parent / "static" / "titan_ad_exporter.html"

POST_FORMAT_OPTIONS = (
    "Standard Feed Post (1:1 Ratio)",
    "Story Format (9:16 Ratio - short text)",
    video_prompts.SHORT_VIDEO_FORMAT,
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
EM_USE_CRITIC = "em_use_critic_pass"
# Per-client suffix: f"{EM_USE_ENGAGEMENT_INSIGHTS_PREFIX}_{client_id}"
EM_USE_ENGAGEMENT_INSIGHTS_PREFIX = "em_use_engagement_insights"
EM_DARK_MODE = "em_dark_mode"
EM_GAP_BUST = "em_gap_cache_bust"

# One-click variety pack: each post randomizes format, pillar, brand & hook.
MIXED_PACK_POST_COUNT = 3
# Pillar pack: one post per pillar × variety (7 total with rotation).
PILLAR_PACK_POST_COUNT = 7

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

OFFROAD_CREATIVE_HOOK_OPTIONS = (
    "Suspension authority: explain one real fitment benefit for SA terrain",
    "Product hero: exact hardware detail and engineering quality in focus",
    "Workshop proof: before/after fitment credibility with practical outcome",
    "Protection build: bumpers/sliders/bash plates and why the setup matters",
    "Recovery readiness: practical gear and safety-first usage context",
    "Myth-bust: what customers get wrong about 4x4 upgrades",
    "Platform-specific angle: Hilux, Land Cruiser, Ranger, Jimny fitment relevance",
    "Brand trust: local SA availability and booking confidence",
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
    if is_offroad_vertical(client):
        return OFFROAD_CREATIVE_HOOK_OPTIONS
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
    """Bento–Halo UI: Athens gray field, white squircle cards, rim-lit chrome, product motion."""
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
            border-bottom: 1px solid rgba(0,0,0,0.06) !important;
          }}
          .block-container {{
            padding-top: 1.5rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1200px !important;
          }}
          .main .block-container p, .main .block-container li, .main label,
          .main [data-testid="stWidgetLabel"] p {{
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 17px !important;
            letter-spacing: 0.02em;
          }}
          .main h1 {{
            font-size: 2rem !important;
            color: {C_HEADING} !important;
            font-family: 'Crimson Pro', 'Georgia', serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.05em;
          }}
          .main h2, .main h3, .main h4 {{
            color: {C_PRIMARY} !important;
            font-family: 'Crimson Pro', 'Georgia', serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.03em;
          }}
          .stCaption, [data-testid="stCaption"] {{
            color: {C_MUTED} !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 0.92rem !important;
            letter-spacing: 0.02em;
          }}

          /* Viewing (top) vs Interaction (bottom) — One UI–style rhythm */
          .em-zone-viewing {{
            min-height: 28vh;
            padding-bottom: 1.25rem;
            margin-bottom: 0.5rem;
          }}
          .em-zone-interaction {{
            padding-top: 0.5rem;
          }}

          /* Bento gutters: 20px between modules */
          div[data-testid="stHorizontalBlock"] {{ gap: 20px !important; }}

          section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #fafafa 0%, {C_SURFACE} 100%) !important;
            border-right: 1px solid rgba(0,0,0,0.06) !important;
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
            letter-spacing: -0.05em;
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
            border-radius: 12px !important;
            min-height: 44px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            font-family: 'Source Sans 3', sans-serif !important;
            letter-spacing: 0.02em;
            width: 100% !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding-left: 12px !important;
            transition: transform 0.22s {C_EASE_PRODUCT}, box-shadow 0.22s {C_EASE_PRODUCT}, background-color 0.22s {C_EASE_PRODUCT} !important;
          }}
          section[data-testid="stSidebar"] .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
          }}
          section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
            background-color: {C_PRIMARY} !important;
            color: #faf8f5 !important;
            border: 1px solid {C_PRIMARY} !important;
          }}
          section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
            background-color: {C_SURFACE} !important;
            color: {C_TEXT} !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
          }}
          section[data-testid="stSidebar"] hr {{
            border-color: rgba(0,0,0,0.06) !important;
            margin: 0.75rem 0 !important;
          }}

          .stButton > button {{
            border-radius: 12px !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            letter-spacing: 0.02em;
            transition: transform 0.22s {C_EASE_PRODUCT}, box-shadow 0.22s {C_EASE_PRODUCT}, background-color 0.22s {C_EASE_PRODUCT}, border-color 0.22s {C_EASE_PRODUCT} !important;
          }}
          .stButton > button:hover {{
            transform: translateY(-1px);
          }}
          .stButton > button[kind="primary"] {{
            background-color: {C_PRIMARY} !important;
            color: #faf8f5 !important;
            border: 1px solid #152a45 !important;
          }}
          .stButton > button[kind="primary"]:hover {{
            background-color: #2a4d75 !important;
            color: #faf8f5 !important;
            box-shadow: 0 6px 20px rgba(30, 58, 95, 0.25);
          }}
          .stButton > button[kind="secondary"] {{
            background-color: {C_SURFACE} !important;
            color: {C_TEXT} !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
          }}
          .stDownloadButton > button {{
            border-radius: 12px !important;
            font-family: 'Source Sans 3', sans-serif !important;
            transition: transform 0.22s {C_EASE_PRODUCT}, box-shadow 0.22s {C_EASE_PRODUCT} !important;
          }}
          .stDownloadButton > button:hover {{
            transform: translateY(-1px);
          }}

          div[data-testid="column"] {{
            background: transparent !important;
            padding: 0 !important;
            border: none !important;
          }}

          /* Squircle-style cards (24px radius — superellipse feel without clipping children) */
          .em-card, .em-panel, .em-squircle {{
            background: {C_SURFACE};
            border: 1px solid {C_BORDER};
            border-radius: 24px;
            padding: 16px 18px;
            margin-bottom: 12px;
            box-shadow:
              0 1px 2px rgba(0,0,0,0.04),
              0 8px 24px rgba(0,0,0,0.06);
            transition: box-shadow 0.25s {C_EASE_PRODUCT}, transform 0.25s {C_EASE_PRODUCT};
          }}
          .em-panel {{
            background: {C_SHARK};
            padding: 14px 16px;
          }}
          .em-bento-tall {{
            min-height: 280px;
          }}
          .em-panel-label {{
            font-size: 0.75rem !important;
            color: {C_MUTED} !important;
            margin: 0 0 8px 0;
            font-family: 'Source Sans 3', sans-serif !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }}
          .em-panel-body {{
            color: {C_TEXT_BODY} !important;
            font-size: 16px !important;
            line-height: 1.5 !important;
            margin: 0;
            font-family: 'Source Sans 3', sans-serif !important;
            letter-spacing: 0.02em;
          }}

          .main [class*="-em_generation_hub"] {{
            border: 1px solid rgba(0,0,0,0.06) !important;
            border-radius: 24px !important;
            padding: 0 !important;
            background: {C_SURFACE} !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 4px 32px rgba(0,0,0,0.07);
            overflow: hidden;
          }}
          .main [class*="-em_generation_hub"] > div {{
            background: {C_SURFACE} !important;
            border: none !important;
            border-radius: 24px !important;
            margin: 0 !important;
            padding: 18px 20px !important;
          }}

          .stTextInput > div > div > input,
          .stTextArea > div > div > textarea,
          .stNumberInput input {{
            border-radius: 12px !important;
            background-color: {C_INPUT_BG} !important;
            color: {C_TEXT_BODY} !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 16px !important;
            letter-spacing: 0.02em;
          }}
          .stSelectbox [data-baseweb="select"] > div {{
            border-radius: 12px !important;
            background-color: {C_INPUT_BG} !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
            min-height: 44px !important;
          }}
          .stSelectbox [data-baseweb="select"] span {{
            font-family: 'Source Sans 3', sans-serif !important;
            font-size: 16px !important;
            color: {C_TEXT_BODY} !important;
            letter-spacing: 0.02em;
          }}
          [data-baseweb="menu"] {{
            background-color: {C_SURFACE} !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
            border-radius: 12px !important;
          }}
          [data-baseweb="menu"] li {{
            font-family: 'Source Sans 3', sans-serif !important;
            color: {C_TEXT_BODY} !important;
          }}

          [data-testid="stExpander"] {{
            background: {C_SURFACE} !important;
            border: 1px solid rgba(0,0,0,0.08) !important;
            border-radius: 20px !important;
          }}
          [data-testid="stExpander"] summary {{
            color: {C_PRIMARY} !important;
            font-family: 'Source Sans 3', sans-serif !important;
            font-weight: 500 !important;
            letter-spacing: 0.02em;
          }}

          div[data-testid="stAlert"] {{
            border-radius: 16px !important;
            border: 1px solid rgba(0,0,0,0.06) !important;
            background-color: {C_SURFACE} !important;
            font-family: 'Source Sans 3', sans-serif !important;
          }}
          div[data-testid="stNotification"], .stSuccess, [data-baseweb="notification"] {{
            font-family: 'Source Sans 3', sans-serif !important;
          }}

          .main [data-testid="stDataFrame"],
          .main [data-testid="stDataFrame"] > div {{
            border-radius: 16px !important;
            border: 1px solid rgba(0,0,0,0.06) !important;
            background: {C_SURFACE} !important;
            font-family: 'Source Sans 3', sans-serif !important;
            letter-spacing: 0.02em;
          }}

          .ui-hero {{
            font-family: 'Crimson Pro', Georgia, serif !important;
            color: {C_HEADING} !important;
            font-size: 2rem !important;
            font-weight: 600 !important;
            line-height: 1.15;
            margin: 0 0 0.5rem 0;
            letter-spacing: -0.05em;
          }}
          .ui-hero-sub {{
            font-family: 'Source Sans 3', sans-serif !important;
            color: {C_MUTED} !important;
            font-size: 1rem !important;
            margin: 0 0 1.25rem 0;
            line-height: 1.5;
            letter-spacing: 0.02em;
          }}
          /* Rim light + inner glow (active client) */
          .ui-active-client {{
            font-family: 'Source Sans 3', sans-serif !important;
            color: {C_TEXT} !important;
            font-size: 1.05rem !important;
            margin: 0 0 1.25rem 0;
            padding: 14px 16px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%);
            border-radius: 0 20px 20px 0;
            border: 1px solid {C_BORDER};
            border-left: 3px solid {C_ACCENT};
            box-shadow:
              inset 0 1px 0 rgba(255,255,255,0.9),
              inset 0 0 10px rgba(255,255,255,0.1),
              0 4px 24px rgba(0,0,0,0.06);
            letter-spacing: 0.02em;
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
            letter-spacing: -0.04em;
          }}
          .em-audit-header-sub {{
            font-size: 0.98rem !important;
            color: {C_MUTED} !important;
            margin: 0 0 0.75rem 0;
            line-height: 1.45;
            font-family: 'Source Sans 3', sans-serif !important;
            letter-spacing: 0.02em;
          }}
          hr {{ border: none !important; border-top: 1px solid rgba(0,0,0,0.06) !important; margin: 1rem 0 !important; }}

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
    if bool(st.session_state.get(EM_DARK_MODE, False)):
        st.markdown(
            """
            <style>
              html, body, .stApp, [data-testid="stAppViewContainer"] {
                background-color: #1c1c1e !important;
                color: #d1d1d6 !important;
              }
              [data-testid="stHeader"] {
                background-color: #2c2c2e !important;
                border-bottom: 1px solid rgba(255,255,255,0.08) !important;
              }
              section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #2c2c2e 0%, #1c1c1e 100%) !important;
                border-right: 1px solid rgba(255,255,255,0.08) !important;
              }
              .em-card, .em-panel, .em-squircle, [data-testid="stExpander"], div[data-testid="stAlert"],
              .main [data-testid="stDataFrame"], .main [data-testid="stDataFrame"] > div {
                background: #2c2c2e !important;
                border-color: rgba(255,255,255,0.12) !important;
                color: #d1d1d6 !important;
              }
              .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stNumberInput input,
              .stSelectbox [data-baseweb="select"] > div {
                background-color: #3a3a3c !important;
                color: #f5f5f7 !important;
                border-color: rgba(255,255,255,0.12) !important;
              }
              .main h1, .main h2, .main h3, .main h4, .ui-hero, .em-audit-header-name { color: #f5f5f7 !important; }
              .ui-active-client {
                background: linear-gradient(180deg, #2c2c2e 0%, #1c1c1e 100%) !important;
                border-color: rgba(255,255,255,0.12) !important;
                color: #f5f5f7 !important;
              }
              .em-zone-viewing, .em-zone-interaction {
                color: #d1d1d6 !important;
              }
              .main [class*="-em_generation_hub"],
              .main [class*="-em_generation_hub"] > div {
                background: #2c2c2e !important;
                border-color: rgba(255,255,255,0.12) !important;
                color: #d1d1d6 !important;
              }
              [data-testid="stMetric"] {
                background: #2c2c2e !important;
                border: 1px solid rgba(255,255,255,0.1) !important;
                border-radius: 16px !important;
              }
              [data-testid="stMetric"] label, [data-testid="stMetric"] [data-testid="stMarkdownContainer"] p {
                color: #a1a1a6 !important;
              }
              [data-testid="stMetricValue"] {
                color: #f5f5f7 !important;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )


def _require_gemini() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        st.error(
            "Set **GEMINI_API_KEY** in `.env` locally, or in **Streamlit Cloud → App settings → Secrets**."
        )
        st.stop()


def _clipboard_button(label: str, text: str) -> None:
    """Client-side copy (Midjourney / Gemini / paste into social tools).

    Note: ``streamlit.components.v1.html`` does not support a ``key=`` argument;
    each call creates a distinct iframe in document order.
    """
    payload = json.dumps(text)
    _dm = bool(st.session_state.get(EM_DARK_MODE, False))
    _bg = "#3a3a3c" if _dm else "#FFFFFF"
    _fg = "#f5f5f7" if _dm else "#1e3a5f"
    _bd = "rgba(255,255,255,0.14)" if _dm else "#CDC6B9"
    components.html(
        f"""
        <button type="button"
          style="padding:0.35rem 0.85rem;border-radius:12px;border:1px solid {_bd};
                 background:{_bg};color:{_fg};cursor:pointer;font-family:'Source Sans 3',system-ui,sans-serif;
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
        _bump_gap_cache()
        st.toast("Delivery status saved.", icon="✅")
        st.rerun()

    return _go


def _engagement_insights_session_key(client_id: int) -> str:
    return f"{EM_USE_ENGAGEMENT_INSIGHTS_PREFIX}_{int(client_id)}"


def _use_engagement_insights_for_client(client: dict) -> bool:
    """Hub toggle; default ON when enough Posted metrics exist (initialized in hub setup)."""
    cid = int(client["id"])
    k = _engagement_insights_session_key(cid)
    if k in st.session_state:
        return bool(st.session_state[k])
    return engagement_learner.client_has_sufficient_engagement_data(cid)


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
    *,
    use_engagement_insights: bool = True,
) -> tuple[dict, str]:
    """Kick off research + creative crew. Returns (parsed JSON, resolved creative hook string)."""
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
    inject_engagement_insights(
        inputs,
        int(client["id"]),
        enabled=use_engagement_insights,
    )
    result = SocialMediaCrew().crew().kickoff(inputs=inputs)
    return parse_crew_json(result.raw), hook


def _few_shot_captions_for_client(client_id: int, *, limit: int = 5) -> str:
    rows = db.get_posts_for_client(client_id)[:limit]
    parts: list[str] = []
    for r in rows:
        cap = (r.get("caption") or "").strip()
        if cap:
            parts.append(cap[:480])
    if not parts:
        return "(no prior posts yet)"
    return "\n---\n".join(parts)


def _run_critic_refinement(
    client: dict,
    draft: dict,
    *,
    content_pillar: str,
    featured_brand: str,
    few_shot: str,
) -> dict:
    os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
    vm = get_vertical_mode(client)
    vrules = get_vertical_creative_rules_for_tasks(client)
    fb = (featured_brand or FEATURED_BRAND_NONE).strip() or FEATURED_BRAND_NONE
    inputs = {
        "company_name": client["company_name"],
        "vertical_mode": vm,
        "vertical_creative_rules": vrules,
        "content_pillar": content_pillar,
        "featured_brand": fb,
        "few_shot_captions": few_shot,
        "draft_json": json.dumps(draft, ensure_ascii=False),
    }
    result = CriticRefinementCrew().crew().kickoff(inputs=inputs)
    return parse_crew_json(result.raw)


def _run_caption_only_regenerate(
    client: dict,
    post: dict,
    *,
    few_shot: str,
) -> str:
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
    fb = (post.get("featured_brand") or FEATURED_BRAND_NONE).strip() or FEATURED_BRAND_NONE
    brand_guidelines = format_brand_guidelines_for_prompt(fb)
    brand_models = format_brand_models_for_prompt(fb)
    vm = get_vertical_mode(client)
    vrules = get_vertical_creative_rules_for_tasks(client)
    bline = "Auto"
    inputs = {
        "company_name": client["company_name"],
        "industry": client["industry"],
        "brand_context": client["brand_context"],
        "tone": tone,
        "services_list": services,
        "target_markets": markets,
        "photography_style": photo_style,
        "post_format": (post.get("post_format") or POST_FORMAT_OPTIONS[0]).strip(),
        "content_pillar": (post.get("content_pillar") or "").strip() or CONTENT_PILLAR_OPTIONS[0],
        "featured_brand": fb,
        "brand_guidelines": brand_guidelines,
        "brand_models": brand_models,
        "battery_featured_line": bline,
        "vertical_mode": vm,
        "vertical_creative_rules": vrules,
        "existing_caption": str(post.get("caption") or ""),
        "existing_image_prompt_square": str(post.get("image_prompt_square") or ""),
        "existing_image_prompt_vertical": str(post.get("image_prompt_vertical") or ""),
        "few_shot_captions": few_shot,
    }
    result = CaptionOnlyCrew().crew().kickoff(inputs=inputs)
    payload = parse_crew_json(result.raw)
    cap = payload.get("Caption")
    if not cap or not str(cap).strip():
        raise ValueError("caption-only task returned empty Caption")
    return str(cap).strip()


def _run_video_prompt_regenerate(
    client: dict,
    post: dict,
    *,
    few_shot: str,
) -> str:
    """Regenerate only Video_Prompt for Short Video posts."""
    if not video_prompts.is_short_video_format(str(post.get("post_format") or "")):
        raise ValueError("Video prompt regeneration applies only to Short Video (9:16) posts")
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
    fb = (post.get("featured_brand") or FEATURED_BRAND_NONE).strip() or FEATURED_BRAND_NONE
    brand_guidelines = format_brand_guidelines_for_prompt(fb)
    brand_models = format_brand_models_for_prompt(fb)
    vm = get_vertical_mode(client)
    vrules = get_vertical_creative_rules_for_tasks(client)
    bline = "Auto"
    inputs = {
        "company_name": client["company_name"],
        "industry": client["industry"],
        "brand_context": client["brand_context"],
        "tone": tone,
        "services_list": services,
        "target_markets": markets,
        "photography_style": photo_style,
        "content_pillar": (post.get("content_pillar") or "").strip() or CONTENT_PILLAR_OPTIONS[0],
        "featured_brand": fb,
        "brand_guidelines": brand_guidelines,
        "brand_models": brand_models,
        "battery_featured_line": bline,
        "vertical_mode": vm,
        "vertical_creative_rules": vrules,
        "existing_caption": str(post.get("caption") or ""),
        "existing_image_prompt_square": str(post.get("image_prompt_square") or ""),
        "existing_image_prompt_vertical": str(post.get("image_prompt_vertical") or ""),
        "existing_video_prompt": str(post.get("video_prompt") or ""),
        "few_shot_captions": few_shot,
    }
    result = VideoPromptOnlyCrew().crew().kickoff(inputs=inputs)
    payload = parse_crew_json(result.raw)
    vp = payload.get("Video_Prompt")
    if not vp or not str(vp).strip():
        raise ValueError("video prompt task returned empty Video_Prompt")
    return str(vp).strip()


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
    elif st.session_state[EM_HUB_POST_FORMAT] not in POST_FORMAT_OPTIONS:
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
        _eid = int(client["id"])
        _eng_k = _engagement_insights_session_key(_eid)
        if _eng_k not in st.session_state:
            st.session_state[_eng_k] = (
                engagement_learner.client_has_sufficient_engagement_data(_eid)
            )


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
    use_critic: bool = False,
    pillar_pack: bool = False,
    use_engagement_insights: bool = True,
    fixed_pillars: tuple[str, ...] | list[str] | None = None,
    finalize_ui: bool = True,
) -> tuple[list[int], list[str]]:
    """CrewAI kickoff + validate JSON + save posts (same path as Authorize).

    If ``mixed_variety`` is True and batch_count > 1, each run also picks a random
    post format (Feed vs Story) for a full content mix.
    If ``pillar_pack`` is True, ``batch_count`` is ignored and seven posts are saved
    with rotating content pillars.

    If ``fixed_pillars`` is set (non-empty) and ``pillar_pack`` is False and ``n > 1``,
    each run uses ``fixed_pillars[i % len(fixed_pillars)]`` as the content pillar.

    When ``finalize_ui`` is False, skip success/toast/rerun/``_bump_gap_cache`` so the
    caller can schedule and finish the UX (returns ``(saved_ids, errors)``).
    """
    n = PILLAR_PACK_POST_COUNT if pillar_pack else int(batch_count)
    angle_for_run = ""
    if n <= 1 and hook_pick != "Random":
        angle_for_run = str(hook_pick)

    saved_ids: list[int] = []
    errors: list[str] = []
    _fs = _few_shot_captions_for_client(int(client["id"]))
    _cname = str(client.get("company_name") or "Client")

    def _one_payload_ok(
        payload: dict, run_label: str, post_format: str
    ) -> tuple[str, str, str, str, str] | None:
        cap = payload.get("Caption")
        ip_sq = payload.get("Image_Generation_Prompt_1_1")
        ip_v = payload.get("Image_Generation_Prompt_9_16")
        legacy = payload.get("Image_Generation_Prompt")
        ov = payload.get("Suggested_Text_Overlay")
        vp_raw = payload.get("Video_Prompt")
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
        if video_prompts.is_short_video_format(post_format):
            vp = str(vp_raw or "").strip()
            if not vp:
                errors.append(
                    f"{run_label}: Video_Prompt is required for Short Video (9:16) format"
                )
                return None
        else:
            vp = ""
        return (
            str(cap).strip(),
            str(ip_sq).strip(),
            str(ip_v).strip(),
            _overlay_to_storage(ov),
            vp,
        )

    try:
        with st.status(
            f"Generating {n} post(s) for {_cname}…",
            expanded=True,
        ) as _status_cm:
            for i in range(n):
                run_label = f"Run {i + 1}/{n}"
                _status_cm.write(
                    f"Generated post {i + 1} of {n} – {_cname}"
                )
                st.session_state["em_gen_progress"] = {
                    "current": i + 1,
                    "total": n,
                    "client": _cname,
                }
                if pillar_pack:
                    pillar = CONTENT_PILLAR_OPTIONS[
                        i % len(CONTENT_PILLAR_OPTIONS)
                    ]
                    brand = random.choice(tuple(brand_choices))
                    angle = ""
                    fmt = random.choice(tuple(POST_FORMAT_OPTIONS))
                    if is_battery_vertical(client):
                        if battery_line_pick == "Random":
                            bline = random.choice(BATTERY_FEATURED_LINE_OPTIONS)
                        else:
                            bline = battery_line_pick
                    else:
                        bline = "Auto"
                elif n <= 1:
                    pillar = content_pillar
                    brand = featured_brand
                    angle = angle_for_run
                    fmt = post_format
                    bline = battery_line_pick
                else:
                    if fixed_pillars and len(fixed_pillars) > 0:
                        pillar = fixed_pillars[i % len(fixed_pillars)]
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
                try:
                    payload, resolved_hook = _run_crew(
                        client,
                        fmt,
                        pillar,
                        brand,
                        creative_angle=angle,
                        battery_featured_line=bline,
                        use_engagement_insights=use_engagement_insights,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{run_label}: CrewAI failed — {exc}")
                    continue
                if use_critic:
                    try:
                        payload = _run_critic_refinement(
                            client,
                            payload,
                            content_pillar=pillar,
                            featured_brand=brand,
                            few_shot=_fs,
                        )
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{run_label}: Critic pass failed — {exc}")
                        continue
                ok = _one_payload_ok(payload, run_label, fmt)
                if ok is None:
                    with st.expander(f"{run_label} — raw JSON (invalid)", expanded=False):
                        st.json(payload)
                    continue
                cap_s, ip_sq, ip_vert, ov_s, vp_s = ok
                pid = db.save_post(
                    int(client["id"]),
                    cap_s,
                    ip_sq,
                    ip_vert,
                    suggested_text_overlay=ov_s,
                    content_pillar=pillar,
                    featured_brand=brand,
                    post_format=fmt,
                    creative_hook=resolved_hook,
                    critic_applied=use_critic,
                    video_prompt=vp_s,
                )
                saved_ids.append(int(pid))
            _status_cm.write("✓ Batch complete.")
    finally:
        pass

    if errors:
        st.error("Some runs failed:\n\n" + "\n\n".join(errors))
    if saved_ids and finalize_ui:
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
        _bump_gap_cache()
        st.rerun()
    return saved_ids, errors


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
        st.toggle("Dark mode", key=EM_DARK_MODE)
        st.divider()
        _av = role_ctx.allowed_sidebar_views()
        dash_primary = st.session_state.current_view == VIEW_DASHBOARD
        analytics_primary = st.session_state.current_view == VIEW_ANALYTICS
        cal_primary = st.session_state.current_view == VIEW_CONTENT_CALENDAR
        onboard_primary = st.session_state.current_view == VIEW_ONBOARD
        overlay_primary = st.session_state.current_view == VIEW_OVERLAY
        if role_ctx.VIEW_DASHBOARD in _av:
            if st.button(
                "Dashboard",
                use_container_width=True,
                key="nav_generation_hub",
                type="primary" if dash_primary else "secondary",
            ):
                st.session_state.current_view = VIEW_DASHBOARD
                st.rerun()
        if role_ctx.VIEW_ANALYTICS in _av:
            if st.button(
                "Analytics",
                use_container_width=True,
                key="nav_analytics",
                type="primary" if analytics_primary else "secondary",
            ):
                st.session_state.current_view = VIEW_ANALYTICS
                st.rerun()
        if role_ctx.VIEW_CONTENT_CALENDAR in _av:
            if st.button(
                "Content Calendar",
                use_container_width=True,
                key="nav_content_cal",
                type="primary" if cal_primary else "secondary",
            ):
                st.session_state.current_view = VIEW_CONTENT_CALENDAR
                st.rerun()
        if role_ctx.VIEW_ONBOARD in _av:
            if st.button(
                "New client",
                use_container_width=True,
                key="nav_onboard_client",
                type="primary" if onboard_primary else "secondary",
            ):
                st.session_state.current_view = VIEW_ONBOARD
                st.rerun()
        if role_ctx.VIEW_OVERLAY in _av:
            if st.button(
                "Overlay studio",
                use_container_width=True,
                key="nav_overlay_studio",
                type="primary" if overlay_primary else "secondary",
            ):
                st.session_state.current_view = VIEW_OVERLAY
                st.rerun()

        if role_ctx.get_current_role() == role_ctx.ROLE_ADMIN:
            st.divider()
            st.markdown(
                f'<p style="color:{C_GRAY};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 6px 0;">'
                f"Role preview</p>",
                unsafe_allow_html=True,
            )
            _r_opts = list(role_ctx.VALID_ROLES)
            _cur_r = role_ctx.get_current_role()
            _ix_r = _r_opts.index(_cur_r) if _cur_r in _r_opts else 0
            st.selectbox(
                "Act as role",
                options=_r_opts,
                index=_ix_r,
                key="em_admin_role_preview",
                label_visibility="collapsed",
                help="Choose which role’s permissions to simulate (sidebar views, hub, captions vs assets, "
                "calendar, bulk actions). Does not change data — use **Switch role** to apply. "
                "External publishers should use the dedicated queue URL.",
            )
            if st.button(
                "Switch role",
                key="em_admin_role_switch",
                use_container_width=True,
                help="Updates the URL (?role=) and session. Clears pending Auto-Pilot / hotkey "
                "generation state; active client and dark mode are kept.",
            ):
                _pick = str(st.session_state.get("em_admin_role_preview", role_ctx.ROLE_ADMIN))
                st.session_state[role_ctx.EM_ROLE_SESSION_KEY] = role_ctx.normalize_role(
                    _pick
                )
                st.query_params["role"] = _pick
                role_ctx.clear_volatile_session_after_role_change()
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
    if not role_ctx.user_can("onboard_client"):
        st.error("Your role cannot create or edit full client profiles.")
        return
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


def _hub_plan_summary_html(client: dict, brand_choices: list[str]) -> str:
    """Plan summary for Bento left rail — driven by session state (matches manual expander logic)."""
    _cn = html.escape(str(client["company_name"]))
    _ind = html.escape(str(client["industry"]))
    batch = int(st.session_state.get(EM_HUB_BATCH, 1))
    post_format = st.session_state.get(EM_HUB_POST_FORMAT, POST_FORMAT_OPTIONS[0])
    if batch <= 1:
        content_pillar = st.session_state.get(EM_HUB_PILLAR, CONTENT_PILLAR_OPTIONS[0])
        featured_brand = st.session_state.get(EM_HUB_BRAND, FEATURED_BRAND_NONE)
        hook_pick = st.session_state.get(EM_HUB_HOOK, "Random")
    else:
        content_pillar = CONTENT_PILLAR_OPTIONS[0]
        featured_brand = FEATURED_BRAND_NONE
        hook_pick = "Random"
    _fmt = html.escape(str(post_format))
    _pil = html.escape(str(content_pillar))
    _fb = html.escape(str(featured_brand))
    _co = (
        f" Co-brand vault: <strong>{_fb}</strong>."
        if featured_brand != FEATURED_BRAND_NONE
        else ""
    )
    if batch <= 1:
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
        _mix_fmt_key = "em_manual_mixed_format"
        _vf = (
            "Feed + Story mixed each run."
            if st.session_state.get(_mix_fmt_key, True)
            else "Single format (left) for all runs."
        )
        _batch_line = (
            f"<strong>{batch}</strong> runs — randomized pillar, brand, hook. {_vf}"
        )
    return (
        f'<div class="em-panel em-bento-tall em-squircle" role="region" aria-label="Plan summary">'
        f'<p class="em-panel-label">Plan summary</p>'
        f'<p class="em-panel-body"><strong>What runs:</strong> Research on <strong>{_cn}</strong> '
        f"(<strong>{_ind}</strong>), then one creative pass → caption + 1:1 & 9:16 image prompts + overlay JSON."
        f"{_co if batch <= 1 else ''}</p>"
        f'<p class="em-panel-body" style="margin-top:0.5rem;">Format: <strong>{_fmt}</strong>. {_batch_line}</p>'
        f"</div>"
    )


def _render_dashboard_hero() -> None:
    st.markdown(
        '<p class="ui-hero">Endpoint Media — Content console</p>'
        '<p class="ui-hero-sub">Select a client in the sidebar, generate posts, copy captions & prompts, '
        "and track delivery.</p>",
        unsafe_allow_html=True,
    )


def _post_datetime_from_row(post: dict) -> datetime | None:
    raw = (post.get("created_at") or "").strip() or (post.get("generated_date") or "").strip()
    if not raw:
        return None
    ts = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extra_gap_alerts(client: dict) -> list[dict]:
    """Vertical-specific gap hints (battery service highlight, etc.)."""
    out: list[dict] = []
    if not is_battery_vertical(client):
        return out
    posts = db.get_posts_for_client(int(client["id"]))
    cutoff = datetime.now(timezone.utc) - timedelta(days=21)
    recent_sh = False
    for p in posts:
        dt = _post_datetime_from_row(p)
        if dt is None or dt < cutoff:
            continue
        if (p.get("content_pillar") or "").strip() == "Service Highlight":
            recent_sh = True
            break
    if not recent_sh:
        out.append(
            {
                "severity": "warning",
                "message": (
                    "⚠️ No **Service Highlight** post in the last **21 days** — consider a "
                    "diagnostics, alternator check, or fitment proof angle."
                ),
            }
        )
    return out


@st.cache_data(ttl=600, show_spinner=False)
def _cached_gap_analysis(
    client_id: int,
    bust: int,
    brands_tuple: tuple[str, ...],
) -> list[dict]:
    """DB-only gap rows; bust increments when posts change so cache invalidates."""
    return db.get_content_gap_analysis(
        client_id,
        content_pillars=CONTENT_PILLAR_OPTIONS,
        featured_brands=brands_tuple,
        brand_none_label=FEATURED_BRAND_NONE,
    )


def _bump_gap_cache() -> None:
    st.session_state[EM_GAP_BUST] = int(st.session_state.get(EM_GAP_BUST, 0)) + 1


def _filter_posts_for_library(
    rows: list[dict],
    *,
    approval_pick: list[str],
    qc_pick: list[str],
    images_mode: str,
    format_pick: list[str],
) -> list[dict]:
    """Apply multiselect / image filters to post rows."""
    out = list(rows)
    if format_pick:
        out = [
            p
            for p in out
            if (p.get("post_format") or "").strip() in format_pick
        ]
    if approval_pick:
        out = [
            p
            for p in out
            if (p.get("approval_stage") or db.APPROVAL_INTERNAL_DRAFT).strip()
            in approval_pick
        ]
    if qc_pick:
        out = [
            p
            for p in out
            if (p.get("qc_status") or db.QC_STATUS_DRAFT).strip() in qc_pick
        ]
    if images_mode == "Has both finals":

        def _both(p: dict) -> bool:
            sq = db.resolve_asset_path(str(p.get("image_square_path") or ""))
            vt = db.resolve_asset_path(str(p.get("image_vertical_path") or ""))
            return sq.is_file() and vt.is_file()

        out = [p for p in out if _both(p)]
    elif images_mode == "Needs images":

        def _missing(p: dict) -> bool:
            sq = db.resolve_asset_path(str(p.get("image_square_path") or ""))
            vt = db.resolve_asset_path(str(p.get("image_vertical_path") or ""))
            return not (sq.is_file() and vt.is_file())

        out = [p for p in out if _missing(p)]
    return out


def _append_post_folder_to_zip(zf: zipfile.ZipFile, post: dict) -> None:
    """Write one post folder into an open ``ZipFile`` (caption, meta, square, vertical)."""
    meta = {
        "post_id": int(post["id"]),
        "client": post.get("client_company_name"),
        "caption_excerpt": (str(post.get("caption") or ""))[:200],
        "publisher_status": post.get("publisher_status"),
        "scheduled_for": post.get("scheduled_for"),
    }
    cid = int(post["client_id"])
    pid = int(post["id"])
    arc_base = f"post_{cid}_{pid}"
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


def _build_post_delivery_zip(post: dict) -> tuple[bytes, str]:
    """ZIP: caption.txt, meta.json, square/vertical files from disk."""
    cid = int(post["client_id"])
    pid = int(post["id"])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        _append_post_folder_to_zip(zf, post)
    name = f"endpoint_post_{cid}_{pid}.zip"
    return buf.getvalue(), name


def _build_publisher_queue_all_zip(posts: list[dict]) -> tuple[bytes, str]:
    """Single ZIP containing each post as `post_{client_id}_{post_id}/` (no nested ZIPs)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for row in posts:
            _append_post_folder_to_zip(zf, row)
    return buf.getvalue(), "publisher_queue_all_posts.zip"


def _publisher_thumbnail_jpeg_path(src: Path, *, max_edge: int = 140) -> str | None:
    """Resize square/vertical asset to a small JPEG for faster queue thumbnails (cached in temp)."""
    if not src.is_file():
        return None
    try:
        stt = src.stat()
        key = hashlib.sha256(
            f"{src.resolve()}|{stt.st_mtime_ns}|{stt.st_size}".encode()
        ).hexdigest()[:20]
    except OSError:
        return str(src)
    dest = Path(tempfile.gettempdir()) / "endpoint_pub_thumbs" / f"{key}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        need = (not dest.is_file()) or (dest.stat().st_mtime < stt.st_mtime)
    except OSError:
        need = True
    if need:
        try:
            im = PILImage.open(src).convert("RGB")
            im.thumbnail((max_edge, max_edge))
            im.save(dest, "JPEG", quality=82, optimize=True)
        except Exception:  # noqa: BLE001
            return str(src)
    return str(dest)


def _render_analytics_dashboard(client: dict) -> None:
    """Per-client metrics + Plotly (last 90d / 12w windows)."""
    _W, _G, _B = _theme_inline()
    _cn = html.escape(str(client.get("company_name") or "Client"))
    st.markdown(
        f'<p class="em-audit-header-title" style="margin-top:0.25rem;">Analytics</p>'
        f'<p class="em-audit-header-name">{_cn}</p>'
        f'<p class="em-audit-header-sub">Engagement, cadence, pillar and <strong>post format</strong> mix — '
        f"last 90 days for pillar/format tables, 12 weeks for weekly cadence.</p>",
        unsafe_allow_html=True,
    )
    snap = analytics.compute_client_analytics(
        int(client["id"]),
        dark_mode=bool(st.session_state.get(EM_DARK_MODE, False)),
    )
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total posts", f"{snap['total_posts']:,}")
    with m2:
        _ar = snap["avg_engagement_rate"]
        st.metric(
            "Avg. engagement rate",
            f"{_ar * 100:.2f}%" if _ar is not None else "—",
            help="Mean of likes ÷ reach where reach > 0",
        )
    with m3:
        st.metric(
            "Most used creative hook",
            snap["top_hook"] or "—",
        )
    with m4:
        st.metric(
            "Top pillar (by avg. rate)",
            snap["top_pillar"] or "—",
            help="Among posts with reach > 0, pillar with highest mean likes/reach",
        )

    st.markdown(
        f'<div class="em-card em-squircle" style="padding:14px 16px;margin-top:10px;">'
        f'<p style="color:{_W};font-weight:600;margin:0 0 8px 0;font-family:Georgia,serif;">'
        f"Posts by approval stage</p></div>",
        unsafe_allow_html=True,
    )
    if snap["by_approval"]:
        st.dataframe(
            pd.DataFrame(
                [{"Stage": k, "Count": v} for k, v in sorted(snap["by_approval"].items())]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No data.")

    st.markdown(
        f'<div class="em-card em-squircle" style="padding:14px 16px;margin-top:14px;">'
        f'<p style="color:{_W};font-weight:600;margin:0 0 8px 0;font-family:Georgia,serif;">'
        f"Posts by content pillar (last 90 days)</p></div>",
        unsafe_allow_html=True,
    )
    if snap["by_pillar_90d"]:
        st.dataframe(
            pd.DataFrame(
                [{"Pillar": k, "Count": v} for k, v in sorted(snap["by_pillar_90d"].items())]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No posts dated in the last 90 days.")

    st.markdown(
        f'<div class="em-card em-squircle" style="padding:14px 16px;margin-top:14px;">'
        f'<p style="color:{_W};font-weight:600;margin:0 0 8px 0;font-family:Georgia,serif;">'
        f"Posts by format (last 90 days)</p></div>",
        unsafe_allow_html=True,
    )
    if snap["by_format_90d"]:
        st.dataframe(
            pd.DataFrame(
                [{"Format": k, "Count": v} for k, v in sorted(snap["by_format_90d"].items())]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No posts dated in the last 90 days.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(snap["fig_weekly"], use_container_width=True)
    with c2:
        st.plotly_chart(snap["fig_scatter"], use_container_width=True)

    st.markdown(
        f'<div class="em-card em-squircle" style="padding:14px 16px;margin-top:22px;">'
        f'<p style="color:{_W};font-weight:600;margin:0 0 8px 0;font-family:Georgia,serif;">'
        f"AI Learning Insights</p>"
        f'<p style="color:{_G};font-size:0.88rem;margin:0 0 12px 0;line-height:1.45;">'
        f"Patterns derived from <strong style=\"color:{_W};\">Posted</strong> posts with likes or reach — "
        f"mirrors what the market researcher may see when “Use past performance insights” is on.</p></div>",
        unsafe_allow_html=True,
    )
    _learn = analytics.build_ai_learning_summary(int(client["id"]))
    st.caption(f"Last learned on: {_learn['computed_at']} (computed live on this view)")
    if _learn.get("insufficient_data_message"):
        st.info(_learn["insufficient_data_message"])
    for _ln in _learn.get("winning_patterns") or []:
        st.markdown(
            f"<p style='margin:6px 0;line-height:1.5;color:{_B};'>"
            f"{html.escape(_ln)}</p>",
            unsafe_allow_html=True,
        )
    _hp = _learn.get("recent_high_performers") or []
    if _hp:
        st.markdown(
            f'<p style="color:{_W};font-weight:600;margin:12px 0 6px 0;font-family:Georgia,serif;">'
            f"Recent standouts (like-rate)</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            pd.DataFrame(_hp),
            use_container_width=True,
            hide_index=True,
        )


def _render_content_calendar(client: dict) -> None:
    """Monthly planning: current month + next 2, scheduled posts, balance mix, day actions."""
    _W, _G, _ = _theme_inline()
    _cid = int(client["id"])
    _cn = html.escape(str(client.get("company_name") or "Client"))
    st.markdown(
        f'<p class="em-audit-header-title" style="margin-top:0.25rem;">Content Calendar</p>'
        f'<p class="em-audit-header-name">{_cn}</p>'
        f'<p class="em-audit-header-sub">Plan slots with <strong style="color:{_W};">scheduled_for</strong> — '
        f"dots show pillar mix; open a day to attach drafts or create a placeholder.</p>",
        unsafe_allow_html=True,
    )
    posts = db.get_posts_for_client(_cid)
    _seq = db.client_post_sequence_by_id(_cid)
    today = date.today()
    m0 = today.replace(day=1)
    months = [m0, content_calendar.add_months(m0, 1), content_calendar.add_months(m0, 2)]
    range_start = content_calendar.month_start_end(months[0].year, months[0].month)[0]
    range_end = content_calendar.month_start_end(months[2].year, months[2].month)[1]
    by_date = content_calendar.posts_by_scheduled_date(posts, range_start, range_end)

    _pick_ex0, _pick_ex1, _pick_ex2 = st.columns([2.2, 1, 1])
    with _pick_ex0:
        _export_i = st.selectbox(
            "Month for export",
            options=[0, 1, 2],
            format_func=lambda i: f"{calendar.month_name[months[i].month]} {months[i].year}",
            key=f"cal_export_month_{_cid}",
            help="Choose which of the three visible calendar months to include in CSV/PDF exports.",
        )
    export_y, export_m = months[int(_export_i)].year, months[int(_export_i)].month
    _sched_export_n = content_calendar.count_scheduled_posts_in_month(posts, export_y, export_m)
    _export_disabled = _sched_export_n == 0
    _cal_client_name = str(client.get("company_name") or "Client")
    _csv_bytes, _csv_fn = content_calendar.month_export_csv_bytes(
        posts,
        client_name=_cal_client_name,
        y=export_y,
        mo=export_m,
    )
    try:
        _pdf_bytes, _pdf_fn = content_calendar.month_export_pdf_bytes(
            posts,
            client_name=_cal_client_name,
            y=export_y,
            mo=export_m,
            pillars=CONTENT_PILLAR_OPTIONS,
        )
    except Exception as _pdf_exc:  # noqa: BLE001
        logger.exception("PDF month export failed")
        _pdf_bytes = b""
        _pdf_fn = "Endpoint_Media_calendar_error.pdf"
    with _pick_ex1:
        st.download_button(
            "Export Month as CSV",
            data=_csv_bytes,
            file_name=_csv_fn,
            mime="text/csv",
            key=f"cal_dl_csv_{_cid}_{export_y}_{export_m}",
            disabled=_export_disabled,
            help="Download scheduled posts as spreadsheet",
            on_click=lambda: st.toast(
                "CSV export ready — check your downloads.", icon="📥"
            ),
        )
    with _pick_ex2:
        st.download_button(
            "Export Month as PDF",
            data=_pdf_bytes,
            file_name=_pdf_fn,
            mime="application/pdf",
            key=f"cal_dl_pdf_{_cid}_{export_y}_{export_m}",
            disabled=_export_disabled or len(_pdf_bytes) == 0,
            help="Branded printable PDF plan",
            on_click=lambda: st.toast(
                "PDF export ready — check your downloads.", icon="📥"
            ),
        )
    if _export_disabled:
        st.caption("Select a month that has at least one scheduled post to enable exports.")
    elif len(_pdf_bytes) == 0:
        st.caption(
            "PDF export failed — ensure **reportlab** is installed (`pyproject.toml` / `pip install reportlab`). "
            "CSV export should still work."
        )

    _bal_y, _bal_m = months[0].year, months[0].month
    if st.button(
        "Balance this month",
        key=f"cal_balance_{_cid}",
        help="Compare scheduled posts in the first visible month to a healthy weekly pillar mix "
        "(targets scale with how many weeks fall in that month). Click again after scheduling to refresh.",
    ):
        _lines = content_calendar.compute_month_balance_lines(
            posts,
            _bal_y,
            _bal_m,
            pillars=CONTENT_PILLAR_OPTIONS,
        )
        st.session_state[f"cal_balance_lines_{_cid}"] = _lines
    if st.session_state.get(f"cal_balance_lines_{_cid}"):
        st.markdown(
            f'<div class="em-card em-squircle" style="padding:14px 16px;margin:10px 0;">'
            f'<p style="color:{_W};font-weight:600;margin:0 0 8px 0;font-family:Georgia,serif;">'
            f"Mix vs targets (scheduled in {_bal_y}-{_bal_m:02d})</p></div>",
            unsafe_allow_html=True,
        )
        for _ln in st.session_state[f"cal_balance_lines_{_cid}"]:
            st.markdown(f"<p style='margin:6px 0;line-height:1.45;'>{_ln}</p>", unsafe_allow_html=True)

    st.markdown(
        f'<p style="color:{_G};font-size:0.88rem;margin:12px 0 6px 0;">Pillar key</p>',
        unsafe_allow_html=True,
    )
    _lk = " · ".join(
        f'<span style="color:{content_calendar.pillar_color(p)};">●</span> {html.escape(p[:18])}'
        for p in CONTENT_PILLAR_OPTIONS
    )
    st.markdown(f"<p style='margin:0 0 10px 0;'>{_lk}</p>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:{_G};font-size:0.82rem;margin:0 0 10px 0;'>"
        f"<strong>Short Video (9:16)</strong> or posts with a motion brief show "
        f"<span style='color:#8a8a8a;'>🎥 Video</span> in the day list.</p>",
        unsafe_allow_html=True,
    )

    _sel_key = f"cal_sel_{_cid}"
    month_cols = st.columns(3, gap="medium")
    for mi, md in enumerate(months):
        yy, mm = md.year, md.month
        with month_cols[mi]:
            st.markdown(
                f'<p style="color:{_W};font-weight:600;font-family:Georgia,serif;margin:0 0 8px 0;">'
                f"{calendar.month_name[mm]} {yy}</p>",
                unsafe_allow_html=True,
            )
            _hdr = st.columns(7)
            for i, wn in enumerate(["M", "T", "W", "T", "F", "S", "S"]):
                _hdr[i].markdown(
                    f"<span style='color:{_G};font-size:0.75rem;'>{wn}</span>",
                    unsafe_allow_html=True,
                )
            for week in calendar.monthcalendar(yy, mm):
                _row = st.columns(7)
                for i, d in enumerate(week):
                    with _row[i]:
                        if d == 0:
                            st.write("")
                        else:
                            _cell = date(yy, mm, d)
                            _n = len(by_date.get(_cell, []))
                            if st.button(
                                f"{d}\n({_n})",
                                key=f"cal_cell_{_cid}_{yy}_{mm}_{d}",
                                use_container_width=True,
                            ):
                                st.session_state[_sel_key] = _cell.isoformat()
                                st.rerun()
                _dots = st.columns(7)
                for i, d in enumerate(week):
                    with _dots[i]:
                        if d == 0:
                            st.write("")
                        else:
                            _cell = date(yy, mm, d)
                            _ps = by_date.get(_cell, [])
                            _dh = "".join(
                                f'<span title="{html.escape(str(p.get("content_pillar") or ""))}" '
                                f'style="display:inline-block;width:7px;height:7px;border-radius:50%;'
                                f'background:{content_calendar.pillar_color(str(p.get("content_pillar") or ""))};'
                                f'margin:0 1px;"></span>'
                                for p in _ps[:8]
                            )
                            st.markdown(
                                f"<div style='text-align:center;min-height:14px;'>{_dh}</div>",
                                unsafe_allow_html=True,
                            )

    _raw_sel = st.session_state.get(_sel_key)
    if _raw_sel:
        try:
            sel_d = date.fromisoformat(str(_raw_sel))
        except ValueError:
            sel_d = None
        if sel_d is not None:
            _iso_slot = content_calendar.noon_utc_iso(sel_d)
            with st.expander(
                f"Day selected — {sel_d.isoformat()}",
                expanded=True,
            ):
                day_posts = by_date.get(sel_d, [])
                if not day_posts:
                    st.caption("No posts scheduled for this day yet.")
                else:
                    st.markdown(
                        f'<p style="color:{_W};font-weight:600;margin:0 0 8px 0;">'
                        f"Scheduled posts</p>",
                        unsafe_allow_html=True,
                    )
                    for _p in day_posts:
                        _pid = int(_p["id"])
                        _pn = _seq.get(_pid, "?")
                        _pill = html.escape(str(_p.get("content_pillar") or "—"))
                        _pf = str(_p.get("post_format") or "")
                        _vid_cal = video_prompts.is_short_video_format(
                            _pf
                        ) or bool(str(_p.get("video_prompt") or "").strip())
                        _vid_badge = (
                            ' <span style="color:#8a8a8a;font-size:0.85em;">🎥 Video</span>'
                            if _vid_cal
                            else ""
                        )
                        st.markdown(
                            f"<p style='margin:4px 0;'><strong>Post #{_pn}</strong> (id {_pid}) · "
                            f"<span style='color:{content_calendar.pillar_color(str(_p.get('content_pillar')))};'>"
                            f"{_pill}</span> · "
                            f"{html.escape(_pf[:40])}{_vid_badge}</p>",
                            unsafe_allow_html=True,
                        )
                st.divider()
                _drafts = [
                    p for p in posts if (p.get("workflow_status") or "") == "Draft"
                ]
                st.markdown("**Schedule an existing draft here**")
                _opts = [0] + [int(p["id"]) for p in _drafts]

                def _cal_draft_fmt(pid: int) -> str:
                    if pid == 0:
                        return "— pick —"
                    _r = next((x for x in _drafts if int(x["id"]) == pid), None)
                    if not _r:
                        return str(pid)
                    return (
                        f"Post #{_seq.get(pid, '?')} (id {pid}) — "
                        f"{str(_r.get('content_pillar') or '—')[:28]}"
                    )

                _pick = st.selectbox(
                    "Draft post",
                    options=_opts,
                    format_func=_cal_draft_fmt,
                    key=f"cal_draft_pick_{_cid}",
                )
                if st.button(
                    "Set scheduled date on draft",
                    key=f"cal_apply_draft_{_cid}",
                    disabled=not role_ctx.user_can("calendar_schedule"),
                ):
                    if _pick == 0:
                        st.error("Select a draft post.")
                    else:
                        db.update_post_scheduled_for(int(_pick), _cid, _iso_slot)
                        _bump_gap_cache()
                        st.success("Scheduled.")
                        st.rerun()
                st.markdown("**Or create a placeholder** (Draft + slot; generate content in Dashboard)")
                _np = st.selectbox(
                    "Pillar for placeholder",
                    options=list(CONTENT_PILLAR_OPTIONS),
                    key=f"cal_new_pillar_{_cid}",
                    disabled=not role_ctx.user_can("calendar_placeholder"),
                )
                if st.button(
                    "Create placeholder post",
                    key=f"cal_placeholder_{_cid}",
                    disabled=not role_ctx.user_can("calendar_placeholder"),
                ):
                    db.create_scheduled_placeholder_post(
                        _cid,
                        content_pillar=_np,
                        scheduled_for_iso=_iso_slot,
                        post_format=POST_FORMAT_OPTIONS[0],
                    )
                    _bump_gap_cache()
                    st.success("Placeholder created — find it in the post library.")
                    st.rerun()
                if st.button(
                    "Clear day selection",
                    key=f"cal_clear_sel_{_cid}",
                    help="Dismiss this day panel and clear the selected date (you can pick another day anytime).",
                ):
                    st.session_state.pop(_sel_key, None)
                    st.rerun()


def _render_publisher_queue() -> None:
    """Private link: external Facebook publisher — no admin login."""
    _pubW, _pubG, _ = _theme_inline()
    st.title("Publisher queue")
    st.caption(
        f"Role: **{role_ctx.ROLE_LABEL_PRETTY.get(role_ctx.get_current_role(), 'Publisher')}** · "
        "Only posts with **QC = Ready for Publisher**. Download assets, copy captions, then schedule or "
        "mark posted on your side."
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
    _all_zip, _all_name = _build_publisher_queue_all_zip(posts)
    st.download_button(
        label="Download all ready posts as ZIP (caption + both images per post)",
        data=_all_zip,
        file_name=_all_name,
        mime="application/zip",
        key="pub_dl_all_zip",
        type="primary",
    )
    _pv_rows: list[dict] = []
    for _p in posts:
        _sq = db.resolve_asset_path(str(_p.get("image_square_path") or ""))
        _vt = db.resolve_asset_path(str(_p.get("image_vertical_path") or ""))
        _sq_disp = _publisher_thumbnail_jpeg_path(_sq) if _sq.is_file() else None
        _vt_disp = _publisher_thumbnail_jpeg_path(_vt) if _vt.is_file() else None
        _pv_rows.append(
            {
                "Square": _sq_disp,
                "Vertical": _vt_disp,
                "Client": str(_p.get("client_company_name") or ""),
                "Post ID": int(_p["id"]),
                "Created": str(_p.get("created_at") or _p.get("generated_date") or "")[:19],
            }
        )
    st.markdown(
        f'<p style="color:{_pubW};font-weight:600;margin:12px 0 6px 0;font-family:Georgia,serif;">'
        f"At a glance</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        pd.DataFrame(_pv_rows),
        column_config={
            "Square": st.column_config.ImageColumn("Square", width="small"),
            "Vertical": st.column_config.ImageColumn("Vertical", width="small"),
            "Client": st.column_config.TextColumn("Client", width="medium"),
            "Post ID": st.column_config.NumberColumn("Post ID", format="%d"),
            "Created": st.column_config.TextColumn("Created"),
        },
        use_container_width=True,
        hide_index=True,
    )
    _cal_pts: list[dict] = []
    for _p in posts:
        _sf = (_p.get("scheduled_for") or "").strip()
        if not _sf:
            continue
        _ts = _sf.replace("Z", "+00:00")
        try:
            _when = datetime.fromisoformat(_ts)
        except ValueError:
            continue
        _cal_pts.append(
            {
                "scheduled": _when,
                "client": str(_p.get("client_company_name") or ""),
                "post_id": int(_p["id"]),
                "platform": str(_p.get("publisher_platform") or ""),
            }
        )
    if _cal_pts:
        _cdf = pd.DataFrame(_cal_pts)
        _fig = go.Figure(
            data=go.Scatter(
                x=_cdf["scheduled"],
                y=_cdf["client"],
                mode="markers",
                marker=dict(size=12, color="#1e3a5f"),
                text=_cdf["post_id"].astype(str),
                customdata=_cdf["platform"],
                hovertemplate="%{x}<br>%{y}<br>Post %{text}<br>%{customdata}<extra></extra>",
            )
        )
        _fig.update_layout(
            title="Scheduled posts (ISO dates in **Scheduled for** only)",
            height=420,
            margin=dict(l=40, r=24, t=48, b=40),
            xaxis_title="When",
            yaxis_title="Client",
        )
        if bool(st.session_state.get(EM_DARK_MODE, False)):
            _fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1c1c1e",
                plot_bgcolor="#1c1c1e",
                font=dict(color="#d1d1d6"),
            )
        st.plotly_chart(_fig, use_container_width=True)

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
                    f'<p style="color:{_pubG};font-size:0.9rem;">'
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
                sq = db.resolve_asset_path(str(row.get("image_square_path") or ""))
                vt = db.resolve_asset_path(str(row.get("image_vertical_path") or ""))
                _thumb_r = st.columns(2)
                with _thumb_r[0]:
                    if sq.is_file():
                        st.image(str(sq), width=160, caption="Square 1:1")
                    else:
                        st.warning("Missing square file on disk.")
                with _thumb_r[1]:
                    if vt.is_file():
                        st.image(str(vt), width=160, caption="Vertical 9:16")
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
                    st.text_input(
                        "Platform (Facebook, Instagram, …)",
                        value=str(row.get("publisher_platform") or ""),
                        key=f"pub_plat_{pid}",
                    )
                    st.text_area(
                        "Notes",
                        value=str(row.get("publisher_notes") or ""),
                        key=f"pub_notes_{pid}",
                    )
                    _pub_ddef = date.today()
                    _raw_pa = (row.get("published_at") or "").strip()
                    if _raw_pa:
                        try:
                            _pub_ddef = datetime.fromisoformat(
                                _raw_pa.replace("Z", "+00:00")
                            ).date()
                        except ValueError:
                            pass
                    st.date_input(
                        "Posted on (when status is **Posted**)",
                        value=_pub_ddef,
                        key=f"pub_date_{pid}",
                    )
                    submitted = st.form_submit_button("Save publisher fields")
                    if submitted:
                        sel = st.session_state.get(f"pub_st_{pid}")
                        sched = st.session_state.get(f"pub_sched_{pid}", "")
                        plat = st.session_state.get(f"pub_plat_{pid}", "")
                        notes = st.session_state.get(f"pub_notes_{pid}", "")
                        mark_now = sel == db.PUBLISHER_POSTED
                        pub_iso: str | None = None
                        if mark_now:
                            d_raw = st.session_state.get(f"pub_date_{pid}")
                            if isinstance(d_raw, date):
                                pub_iso = datetime(
                                    d_raw.year,
                                    d_raw.month,
                                    d_raw.day,
                                    12,
                                    0,
                                    0,
                                    tzinfo=timezone.utc,
                                ).isoformat()
                        db.update_post_publisher_fields(
                            pid,
                            publisher_status=str(sel),
                            scheduled_for=str(sched),
                            publisher_notes=str(notes),
                            publisher_platform=str(plat),
                            set_published_now=mark_now,
                            published_at_iso=pub_iso if mark_now else None,
                        )
                        for _k in (
                            f"pub_st_{pid}",
                            f"pub_sched_{pid}",
                            f"pub_plat_{pid}",
                            f"pub_notes_{pid}",
                            f"pub_date_{pid}",
                        ):
                            st.session_state.pop(_k, None)
                        st.success("Saved.")
                        st.rerun()


def _render_overlay_studio(clients: list[dict]) -> None:
    """Titan-style HTML exporter (html2canvas) — matches your prototype layout."""
    _ = clients  # reserved if we later inject DB-driven presets into the iframe
    if not role_ctx.user_can("view_overlay_studio"):
        st.warning("Your role cannot access Overlay studio.")
        return
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
        "Presets: Alberton Tyre Clinic, Alberton Battery Mart, Miwesu Fire Wood, Absolute Offroad. "
        "**Faster workflow:** use the in-app **Generate assets** baker on each post (Dashboard → post card → "
        "**Generate assets** — Imagen + overlay + JPEG save) instead of exporting from here."
    )


def _render_client_review(post: dict) -> None:
    """Public token link — client feedback without editing the full dashboard."""
    pid = int(post["id"])
    cid = int(post["client_id"])
    cname = ""
    for c in db.get_all_clients():
        if int(c["id"]) == cid:
            cname = str(c.get("company_name") or "")
            break
    st.markdown(
        f'<div class="em-card em-squircle" style="max-width:960px;margin:0 auto 1.25rem auto;">'
        f'<p style="color:{C_MUTED};font-size:0.75rem;text-transform:uppercase;letter-spacing:0.12em;margin:0 0 6px 0;">'
        f"Client review</p>"
        f'<p style="font-family:Georgia,serif;font-size:2rem;font-weight:600;color:{C_HEADING};margin:0;line-height:1.15;">'
        f"{html.escape(cname or f'Client #{cid}')}</p>"
        f'<p style="color:{C_GRAY};margin:8px 0 0 0;font-size:1rem;">Review your creative. Approve or request changes — the studio sees updates instantly.</p>'
        f"</div>",
        unsafe_allow_html=True,
    )
    _sq = db.resolve_asset_path(str(post.get("image_square_path") or ""))
    _vt = db.resolve_asset_path(str(post.get("image_vertical_path") or ""))
    ir, ic = st.columns(2, gap="large")
    with ir:
        st.markdown(
            f'<p style="color:{C_PRIMARY};font-weight:600;margin:0 0 8px 0;">Square — 1:1</p>',
            unsafe_allow_html=True,
        )
        if _sq.is_file():
            st.image(PILImage.open(_sq), use_container_width=True)
        else:
            st.info("Square asset not uploaded yet — the studio will add it.")
    with ic:
        st.markdown(
            f'<p style="color:{C_PRIMARY};font-weight:600;margin:0 0 8px 0;">Vertical — 9:16</p>',
            unsafe_allow_html=True,
        )
        if _vt.is_file():
            st.image(PILImage.open(_vt), use_container_width=True)
        else:
            st.info("Vertical asset not uploaded yet — the studio will add it.")

    st.markdown(
        f'<p style="color:{C_WHITE};font-weight:600;margin-top:1rem;">Caption</p>',
        unsafe_allow_html=True,
    )
    _cap = str(post.get("caption") or "")
    st.text_area(
        "Caption",
        value=_cap,
        height=min(260, 100 + len(_cap) // 4),
        disabled=True,
        label_visibility="collapsed",
        key=f"cr_cap_ro_{pid}",
    )
    _clipboard_button("Copy caption", _cap)

    fb = st.text_area(
        "Feedback for the studio",
        key=f"cr_fb_{pid}",
        height=120,
        placeholder="What should we adjust? Wording, imagery, timing…",
    )
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Approve", type="primary", use_container_width=True, key=f"cr_apr_{pid}"):
            if _sq.is_file() and _vt.is_file():
                db.set_post_qc_ready(pid)
                st.success("Approved — **Ready for Publisher** (both finals on file).")
            else:
                db.update_post_approval_stage(pid, db.APPROVAL_APPROVED)
                st.success("Approved — the studio will add finals before the publisher queue.")
            st.rerun()
    with b2:
        if st.button("Request changes", use_container_width=True, key=f"cr_req_{pid}"):
            db.set_client_review_comment(pid, str(st.session_state.get(f"cr_fb_{pid}", "")))
            db.update_post_approval_stage(pid, db.APPROVAL_CLIENT_REVIEW)
            st.success("Feedback saved — the studio will revise.")
            st.rerun()
    with b3:
        st.caption(
            f"Stage: **{(post.get('approval_stage') or '—')}** · "
            f"QC: **{(post.get('qc_status') or '—')}**"
        )


def main() -> None:
    st.set_page_config(
        page_title="Endpoint Media — Content",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    if EM_DARK_MODE not in st.session_state:
        st.session_state[EM_DARK_MODE] = False
    if EM_USE_CRITIC not in st.session_state:
        st.session_state[EM_USE_CRITIC] = False
    if EM_GAP_BUST not in st.session_state:
        st.session_state[EM_GAP_BUST] = 0
    # Must run after set_page_config (first Streamlit call); secrets → os.environ for CrewAI.
    _hydrate_env_from_streamlit_secrets()
    _inject_classical_theme()
    db.init_db()

    _qp_view = st.query_params.get("view")
    role_ctx.init_role_from_query_params(
        publisher_view=(str(_qp_view or "").strip() == "publisher"),
    )

    _qp_tok = (st.query_params.get("token") or "").strip()
    if _qp_view == "client_review" and _qp_tok:
        row = db.get_post_by_client_review_token(_qp_tok)
        if not row:
            st.error("Invalid or expired review link.")
            st.stop()
        _render_client_review(row)
        return

    if _qp_view == "publisher":
        _key = (st.query_params.get("key") or "").strip()
        _expected = os.getenv("PUBLISHER_SHARED_KEY", "").strip()
        if not _expected or _key != _expected:
            st.error("Invalid or missing publisher link. Ask the studio for the current URL.")
            st.stop()
        _render_publisher_queue()
        return

    if str(_qp_view or "").strip() != "publisher":
        if role_ctx.get_current_role() == role_ctx.ROLE_PUBLISHER:
            with st.sidebar:
                st.markdown(
                    f'<p class="ui-sidebar-title">Endpoint Media</p>',
                    unsafe_allow_html=True,
                )
                st.caption("Publisher role")
                st.markdown(
                    "The publisher queue opens from the **shared link** only. "
                    "Switch back to Admin to use the full console."
                )
                if st.button("Exit to Admin", key="em_role_pub_exit", use_container_width=True):
                    st.session_state[role_ctx.EM_ROLE_SESSION_KEY] = role_ctx.ROLE_ADMIN
                    st.query_params["role"] = "admin"
                    st.rerun()
            st.warning(
                "Publisher role is for the external queue page only. "
                "Use the studio link, or click **Exit to Admin** in the sidebar."
            )
            st.stop()

    if "current_view" not in st.session_state:
        st.session_state.current_view = VIEW_DASHBOARD
    role_ctx.enforce_current_view_for_role()

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
    if st.session_state.current_view == VIEW_ANALYTICS:
        if not clients:
            st.warning("Add a client first.")
            return
        _ensure_active_client_id(clients)
        _cid_a = int(st.session_state[EM_ACTIVE_CLIENT_ID])
        _client_a = _client_by_id(clients, _cid_a)
        if _client_a is None:
            _ensure_active_client_id(clients)
            _cid_a = int(st.session_state[EM_ACTIVE_CLIENT_ID])
            _client_a = _client_by_id(clients, _cid_a)
        if _client_a is None:
            st.error("Pick a client in the sidebar.")
            st.stop()
        st.markdown('<div class="em-zone em-zone-viewing">', unsafe_allow_html=True)
        _render_analytics_dashboard(_client_a)
        st.markdown("</div>", unsafe_allow_html=True)
        return
    if st.session_state.current_view == VIEW_CONTENT_CALENDAR:
        if not clients:
            st.warning("Add a client first.")
            return
        _ensure_active_client_id(clients)
        _cid_c = int(st.session_state[EM_ACTIVE_CLIENT_ID])
        _client_c = _client_by_id(clients, _cid_c)
        if _client_c is None:
            _ensure_active_client_id(clients)
            _cid_c = int(st.session_state[EM_ACTIVE_CLIENT_ID])
            _client_c = _client_by_id(clients, _cid_c)
        if _client_c is None:
            st.error("Pick a client in the sidebar.")
            st.stop()
        st.markdown('<div class="em-zone em-zone-viewing">', unsafe_allow_html=True)
        _render_content_calendar(_client_c)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # --- Viewing zone (top): hero, context, content gaps — One UI "see first" ---
    st.markdown('<div class="em-zone em-zone-viewing">', unsafe_allow_html=True)
    _render_dashboard_hero()

    if not clients:
        st.markdown(
            f'<div class="em-card em-squircle"><p style="color:{C_ATHENS};margin:0;">'
            f"No clients yet. In the sidebar, click "
            f'<strong style="color:{C_TEXT};">{VIEW_ONBOARD}</strong> to add one.</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
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
    _rl = role_ctx.ROLE_LABEL_PRETTY.get(
        role_ctx.get_current_role(),
        role_ctx.get_current_role(),
    )
    st.markdown(
        f'<p class="ui-active-client">Active client: '
        f'<span class="ui-accent">{_cn_disp}</span> &nbsp;&middot;&nbsp; profile #{_cid}</p>'
        f'<p style="color:{C_GRAY};font-size:0.88rem;margin:6px 0 0 0;">'
        f"Working as <strong style=\"color:{C_TEXT};\">{html.escape(_rl)}</strong>"
        f" &nbsp;&middot;&nbsp; "
        f'<span style="opacity:0.92;">Role controls sidebar and actions</span></p>',
        unsafe_allow_html=True,
    )
    _ensure_hub_widget_state(
        _crew_brands_for_client(client, brand_choices),
        client=client,
    )

    try:
        if st.query_params.get("hotkey_gen") == "1":
            st.session_state["_hotkey_run_pipeline"] = True
            del st.query_params["hotkey_gen"]
    except Exception:  # noqa: BLE001
        if st.query_params.get("hotkey_gen") == "1":
            st.session_state["_hotkey_run_pipeline"] = True

    st.markdown(
        f'<p class="em-audit-header-title" style="margin-top:0.5rem;">Content intelligence</p>'
        f'<p class="em-audit-header-name" style="font-size:1.1rem;">Gaps · last 30 days</p>',
        unsafe_allow_html=True,
    )
    _gap_bust = int(st.session_state.get(EM_GAP_BUST, 0))
    _br_t = tuple(_gap_featured_brands_for_analysis(client, brand_choices))
    _alerts = list(
        _cached_gap_analysis(
            _cid,
            _gap_bust,
            _br_t,
        )
    )
    _alerts.extend(_extra_gap_alerts(client))
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
                    disabled=not role_ctx.user_can("gap_fill_generate"),
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
                        use_critic=st.session_state.get(EM_USE_CRITIC, False),
                        use_engagement_insights=_use_engagement_insights_for_client(
                            client
                        ),
                    )

    st.markdown("</div>", unsafe_allow_html=True)

    # --- Interaction zone (bottom): generation + library — reachability / controls ---
    st.markdown('<div class="em-zone em-zone-interaction">', unsafe_allow_html=True)

    with st.container(border=True, key="em_generation_hub", gap="medium"):
        _W, _G, _B = _theme_inline()
        _batch_sched_key = f"em_batch_sched_result_{_cid}"
        if _batch_sched_key in st.session_state:
            st.markdown(
                st.session_state[_batch_sched_key]["message"],
                unsafe_allow_html=True,
            )
            _bca, _bcb = st.columns(2)
            with _bca:
                if st.button(
                    "Go to Content Calendar",
                    key=f"{_batch_sched_key}_goto_cal",
                    use_container_width=True,
                ):
                    st.session_state.pop(_batch_sched_key, None)
                    st.session_state.current_view = VIEW_CONTENT_CALENDAR
                    st.rerun()
            with _bcb:
                if st.button(
                    "Stay here",
                    key=f"{_batch_sched_key}_stay",
                    use_container_width=True,
                ):
                    st.session_state.pop(_batch_sched_key, None)
                    st.rerun()
            st.divider()
        if not role_ctx.user_can("generate_crew"):
            if role_ctx.get_current_role() == role_ctx.ROLE_DESIGNER:
                st.info(
                    "**Designer:** CrewAI text generation (hub buttons, mixed/pillar packs, gap-fill, Auto-Pilot) "
                    "is hidden — that is intentional. You still have **Generate assets** (Imagen, overlay, JPEG save) "
                    "on each post and **Overlay studio** in the sidebar."
                )
            else:
                st.info("Generation controls are restricted for this role.")
        _bc_l, _bc_r = st.columns([5, 7], gap="large")
        with _bc_l:
            st.markdown(
                _hub_plan_summary_html(client, list(_crew_brands_for_client(client, brand_choices))),
                unsafe_allow_html=True,
            )
        with _bc_r:
            st.markdown("#### Generate")
            components.html(
                """
                <script>
                (function() {
                  function go(e) {
                    if ((e.ctrlKey || e.metaKey) && (e.key === 'g' || e.key === 'G')) {
                      e.preventDefault();
                      try {
                        var u = new URL(window.parent.location.href);
                        u.searchParams.set('hotkey_gen', '1');
                        window.parent.location.href = u.toString();
                      } catch (err) {}
                    }
                  }
                  window.addEventListener('keydown', go);
                })();
                </script>
                """,
                height=0,
            )

            # Auto-Pilot must mutate hub keys before selectboxes/inputs with those keys run.
            if st.session_state.pop(EM_PENDING_AUTOPILOT, False) and role_ctx.user_can(
                "generate_crew"
            ):
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
                    use_critic=st.session_state.get(EM_USE_CRITIC, False),
                    use_engagement_insights=_use_engagement_insights_for_client(
                        client
                    ),
                )

            _cn = html.escape(str(client["company_name"]))
            _ind = html.escape(str(client["industry"]))
            st.markdown(
                f'<div class="em-card em-squircle" style="margin-top:4px;">'
                f'<p style="color:{_W};font-size:1.2rem;font-weight:600;margin:0 0 4px 0;letter-spacing:-0.02em;">{_cn}</p>'
                f'<p style="color:{_G};margin:0 0 4px 0;letter-spacing:0.02em;">{_ind}</p></div>',
                unsafe_allow_html=True,
            )
            if is_firewood_vertical(client):
                _mix_intro = (
                    f"<p style='color:{_B};font-size:1.02rem;margin:0 0 16px 0;'>"
                    f"Click once to create <strong style='color:{_W};'>{MIXED_PACK_POST_COUNT} posts</strong> "
                    f"with a random mix of pillars (service, education, promo, authority), "
                    f"<strong style='color:{_W};'>Feed + Story</strong> formats, and creative hooks—"
                    f"delivery, braai/coals, product hero, did-you-know, and promo angles driven by your brief "
                    f"(wood lines, moisture/dry story, Gauteng delivery, WhatsApp orders). "
                    f"<strong style='color:{_W};'>No tyre co-brands</strong> for this client.</p>"
                )
            elif is_battery_vertical(client):
                _mix_intro = (
                    f"<p style='color:{_B};font-size:1.02rem;margin:0 0 16px 0;'>"
                    f"Click once to create <strong style='color:{_W};'>{MIXED_PACK_POST_COUNT} posts</strong> "
                    f"with a random mix of pillars (service, education, promo, authority), "
                    f"<strong style='color:{_W};'>Feed + Story</strong> formats, and hooks—"
                    f"battery diagnostics, mobile callouts, fitment, and backup power angles from your brief. "
                    f"<strong style='color:{_W};'>No tyre co-brands</strong> for this client.</p>"
                )
            else:
                _mix_intro = (
                    f"<p style='color:{_B};font-size:1.02rem;margin:0 0 16px 0;'>"
                    f"Click once to create <strong style='color:{_W};'>{MIXED_PACK_POST_COUNT} posts</strong> "
                    f"with a random mix of pillars (service, education, promo, authority), "
                    f"<strong style='color:{_W};'>Feed + Story</strong> formats, "
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
                if st.button(
                    "Save photography style",
                    key=f"save_photo_style_{_pid}",
                    disabled=not role_ctx.user_can("edit_client_photography_style"),
                ):
                    db.update_client(_pid, photography_style=str(st.session_state.get(_ph_key) or ""))
                    st.session_state.pop(_ph_key, None)
                    st.success("Photography style saved.")
                    st.rerun()

            _eng_k_hub = _engagement_insights_session_key(int(client["id"]))
            st.checkbox(
                "Use past performance insights",
                key=_eng_k_hub,
                help="When enough Posted posts have likes or reach, the market researcher gets a short "
                "performance summary (same idea as Analytics → AI Learning Insights). "
                "Uncheck to skip that for every hub run: mixed pack, pillar pack, manual batch, gap-fill, "
                "Auto-Pilot, and Ctrl+G. Per-client setting persists while you switch views.",
                disabled=not role_ctx.user_can("engagement_insights_toggle"),
            )

            st.caption(
                f"⏱ {MIXED_PACK_POST_COUNT} sequential AI runs — usually about a minute or two total. "
                "Watch the **status** panel for each step; failed runs are listed without stopping the batch."
            )
            if st.button(
                f"Generate {MIXED_PACK_POST_COUNT} mixed posts",
                type="primary",
                use_container_width=True,
                key="em_generate_mixed_pack",
                disabled=not role_ctx.user_can("generate_crew"),
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
                    use_critic=st.session_state.get(EM_USE_CRITIC, False),
                    use_engagement_insights=_use_engagement_insights_for_client(
                        client
                    ),
                )

            st.caption(
                f"⏱ {PILLAR_PACK_POST_COUNT} sequential runs — rotates through all four content pillars."
            )
            if st.button(
                f"Generate {PILLAR_PACK_POST_COUNT}-post pillar pack",
                type="secondary",
                use_container_width=True,
                key="em_generate_pillar_pack",
                disabled=not role_ctx.user_can("generate_crew"),
            ):
                _execute_generation_pipeline(
                    client,
                    POST_FORMAT_OPTIONS[0],
                    1,
                    CONTENT_PILLAR_OPTIONS[0],
                    FEATURED_BRAND_NONE,
                    "Random",
                    "Random" if is_battery_vertical(client) else "Auto",
                    _crew_brands_for_client(client, brand_choices),
                    mixed_variety=True,
                    use_critic=st.session_state.get(EM_USE_CRITIC, False),
                    pillar_pack=True,
                    use_engagement_insights=_use_engagement_insights_for_client(
                        client
                    ),
                )

            with st.expander("Manual generation — one post, custom batch, or Auto-Pilot", expanded=False):
                col_format, col_batch = st.columns(2, gap="large")

                with col_format:
                    st.markdown(
                        f'<p style="color:{_G};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Post format</p>',
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
                        f'<p style="color:{_G};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Batch size</p>',
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
                            f'<p style="color:{_G};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Content pillar</p>',
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
                            f'<p style="color:{_G};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Featured brand</p>',
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
                            f'<p style="color:{_G};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;">Creative hook</p>',
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
                            f'<p style="color:{_G};font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em;margin:10px 0 8px 0;">Battery featured line</p>',
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
                        f'<p style="color:{_G};"><strong style="color:{_W};">Tone</strong> · '
                        f'{html.escape(str(client.get("tone") or "—"))}</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p style="color:{_G};"><strong style="color:{_W};">Services</strong> · '
                        f'{html.escape(str(client.get("services_list") or "—"))}</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p style="color:{_G};"><strong style="color:{_W};">Markets</strong> · '
                        f'{html.escape(str(client.get("target_markets") or "—"))}</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p style="color:{_G};"><strong style="color:{_W};">Photography & visual</strong> · '
                        f'{html.escape(str(client.get("photography_style") or "—"))}</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p style="color:{_B};">{html.escape(str(client["brand_context"]))}</p>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    "<div style='height:8px;' aria-hidden='true'></div>",
                    unsafe_allow_html=True,
                )
                st.checkbox(
                    "Apply critic pass (extra QA on caption + prompts)",
                    key=EM_USE_CRITIC,
                    disabled=not role_ctx.user_can("critic_pass"),
                )
                btn_auth, btn_auto = st.columns(2, gap="medium")
                with btn_auth:
                    if st.button(
                        "Run generation",
                        type="primary",
                        use_container_width=True,
                        key="em_authorize_execute",
                        disabled=not role_ctx.user_can("generate_crew"),
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
                            use_critic=st.session_state.get(EM_USE_CRITIC, False),
                            use_engagement_insights=_use_engagement_insights_for_client(
                                client
                            ),
                        )
                with btn_auto:
                    if st.button(
                        "Auto-Pilot (random settings)",
                        type="secondary",
                        use_container_width=True,
                        key="em_autopilot_surprise",
                        help="Random format, pillar, brand & hook—then runs the same CrewAI save pipeline.",
                        disabled=not role_ctx.user_can("generate_crew"),
                    ):
                        st.session_state[EM_PENDING_AUTOPILOT] = True
                        st.rerun()

                st.markdown(
                    f'<p style="color:{_G};font-size:0.85rem;margin:6px 0 0 0;">'
                    f"Tip: <strong style=\"color:{_W};\">Ctrl+G</strong> (Windows/Linux) or "
                    f"<strong style=\"color:{_W};\">⌘+G</strong> (Mac) runs generation with the "
                    f"current hub settings.</p>",
                    unsafe_allow_html=True,
                )
                if st.session_state.pop("_hotkey_run_pipeline", False):
                    if not role_ctx.user_can("generate_crew"):
                        st.warning("Your role cannot run CrewAI generation.")
                    else:
                        _bc_run = int(st.session_state.get(EM_HUB_BATCH, 1))
                        _pf_run = st.session_state.get(EM_HUB_POST_FORMAT, POST_FORMAT_OPTIONS[0])
                        _mix_key_hot = "em_manual_mixed_format"
                        if _bc_run <= 1:
                            _pil_run = st.session_state.get(
                                EM_HUB_PILLAR, CONTENT_PILLAR_OPTIONS[0]
                            )
                            _fb_run = st.session_state.get(EM_HUB_BRAND, FEATURED_BRAND_NONE)
                            _hk_run = st.session_state.get(EM_HUB_HOOK, "Random")
                        else:
                            _pil_run = CONTENT_PILLAR_OPTIONS[0]
                            _fb_run = FEATURED_BRAND_NONE
                            _hk_run = "Random"
                        _bl_run = st.session_state.get(EM_HUB_BATTERY_LINE, "Auto")
                        _manual_mixed_hot = _bc_run > 1 and st.session_state.get(
                            _mix_key_hot, True
                        )
                        _execute_generation_pipeline(
                            client,
                            _pf_run,
                            _bc_run,
                            _pil_run,
                            _fb_run,
                            _hk_run,
                            _bl_run,
                            _crew_brands_for_client(client, brand_choices),
                            mixed_variety=_manual_mixed_hot,
                            use_critic=st.session_state.get(EM_USE_CRITIC, False),
                            use_engagement_insights=_use_engagement_insights_for_client(
                                client
                            ),
                        )

            _can_batch_sched = role_ctx.user_can("generate_crew") and role_ctx.user_can(
                "calendar_schedule"
            )
            if _can_batch_sched:
                with st.expander(
                    "Advanced: Generate & Auto-Schedule Batch",
                    expanded=False,
                ):
                    st.markdown(
                        '<div class="em-panel em-squircle" style="padding:12px 14px;margin-bottom:12px;">',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        '<p class="em-panel-label" style="margin-top:0;">Batch + calendar</p>'
                        '<p class="em-panel-body" style="margin:0;">Run CrewAI for many posts at once, then '
                        "assign <strong>scheduled_for</strong> (noon UTC) across your chosen window. "
                        "Pillars can rotate evenly or follow the same deficit logic as "
                        "<strong>Balance this month</strong>.</p>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                    _n_auto = st.selectbox(
                        "Number of posts",
                        options=[7, 14, 21, 30],
                        index=0,
                        key=f"em_auto_sched_n_{_cid}",
                    )
                    _period_labels = (
                        ("Next 30 days", content_calendar.PERIOD_NEXT_30_DAYS),
                        ("This calendar month", content_calendar.PERIOD_THIS_CALENDAR_MONTH),
                        ("Next calendar month", content_calendar.PERIOD_NEXT_CALENDAR_MONTH),
                    )
                    _period_pick = st.selectbox(
                        "Target period",
                        options=list(range(len(_period_labels))),
                        format_func=lambda i: _period_labels[i][0],
                        key=f"em_auto_sched_period_{_cid}",
                    )
                    _period_key_run = _period_labels[int(_period_pick)][1]
                    _bal_pick = st.radio(
                        "Balance mode (content pillars)",
                        options=("even", "balance"),
                        format_func=lambda x: (
                            "Even distribution across pillars"
                            if x == "even"
                            else "Follow monthly balance recommendation"
                        ),
                        horizontal=True,
                        key=f"em_auto_sched_bal_{_cid}",
                    )
                    _eng_auto_k = f"em_auto_sched_eng_{_cid}"
                    if _eng_auto_k not in st.session_state:
                        st.session_state[_eng_auto_k] = _use_engagement_insights_for_client(
                            client
                        )
                    st.checkbox(
                        "Use past performance insights",
                        key=_eng_auto_k,
                        help="Matches the main hub toggle when first opened; adjust per batch as needed.",
                        disabled=not role_ctx.user_can("engagement_insights_toggle"),
                    )
                    _mix_auto_k = f"em_auto_sched_mixfmt_{_cid}"
                    if _mix_auto_k not in st.session_state:
                        st.session_state[_mix_auto_k] = True
                    st.checkbox(
                        "Mixed format (1:1, 9:16 Story, Short Video)",
                        key=_mix_auto_k,
                        help="Randomize format each run (like manual batch + mixed variety).",
                    )
                    st.caption(
                        "Uses **Apply critic pass** from the manual section above when enabled."
                    )
                    if st.button(
                        "Run Batch & Schedule",
                        type="primary",
                        use_container_width=True,
                        key=f"em_auto_sched_run_{_cid}",
                    ):
                        _anchor_d = date.today()
                        _posts_snapshot = db.get_posts_for_client(_cid)
                        _by_y, _by_mo = content_calendar.balance_context_month(
                            _period_key_run, _anchor_d
                        )
                        if _bal_pick == "even":
                            _pseq = content_calendar.pillar_sequence_even(
                                int(_n_auto), CONTENT_PILLAR_OPTIONS
                            )
                        else:
                            _pseq = content_calendar.pillar_sequence_balance(
                                _posts_snapshot,
                                _by_y,
                                _by_mo,
                                int(_n_auto),
                                CONTENT_PILLAR_OPTIONS,
                            )
                        _eng_run = bool(st.session_state.get(_eng_auto_k, True))
                        if not role_ctx.user_can("engagement_insights_toggle"):
                            _eng_run = False
                        _mix_run = bool(st.session_state.get(_mix_auto_k, True))
                        _bl_auto = (
                            "Random"
                            if is_battery_vertical(client)
                            else "Auto"
                        )
                        _saved_ids, _err_list = _execute_generation_pipeline(
                            client,
                            POST_FORMAT_OPTIONS[0],
                            int(_n_auto),
                            CONTENT_PILLAR_OPTIONS[0],
                            FEATURED_BRAND_NONE,
                            "Random",
                            _bl_auto,
                            _crew_brands_for_client(client, brand_choices),
                            mixed_variety=_mix_run,
                            use_critic=st.session_state.get(EM_USE_CRITIC, False),
                            use_engagement_insights=_eng_run,
                            fixed_pillars=tuple(_pseq),
                            finalize_ui=False,
                        )
                        if _err_list:
                            st.error(
                                "Some generation steps failed:\n\n"
                                + "\n\n".join(_err_list)
                            )
                        if _saved_ids:
                            _rs, _re, _ = content_calendar.auto_schedule_posts(
                                _cid,
                                _saved_ids,
                                period_key=_period_key_run,
                                anchor=_anchor_d,
                            )
                            _bump_gap_cache()
                            _plab = {
                                content_calendar.PERIOD_NEXT_30_DAYS: "the next 30 days",
                                content_calendar.PERIOD_THIS_CALENDAR_MONTH: "the rest of this calendar month",
                                content_calendar.PERIOD_NEXT_CALENDAR_MONTH: "next calendar month",
                            }[_period_key_run]
                            st.session_state[_batch_sched_key] = {
                                "message": (
                                    f"<p style='margin:0 0 8px 0;'>Successfully created and scheduled "
                                    f"<strong>{len(_saved_ids)}</strong> posts for <strong>{_plab}</strong> "
                                    f"({_rs.isoformat()} → {_re.isoformat()}). "
                                    f"View them in <strong>Content Calendar</strong>.</p>"
                                ),
                            }
                            st.toast(
                                f"Created and scheduled {len(_saved_ids)} posts.",
                                icon="📅",
                            )
                            st.rerun()
                        elif not _err_list:
                            st.warning("No posts were saved — nothing to schedule.")

    _lpW, _lpG, _ = _theme_inline()
    st.markdown(
        f'<p class="em-audit-header-title" style="margin-top:2.5rem;">Post library</p>'
        f'<p class="em-audit-header-name">Asset delivery &amp; delivery tracking</p>'
        f'<p class="em-audit-header-sub">Copy captions and image prompts into Midjourney, Gemini, or your '
        f"design stack. Update status as you send work to clients and when it goes live.</p>",
        unsafe_allow_html=True,
    )
    posts_all = db.get_posts_for_client(int(client["id"]))
    if not posts_all:
        st.markdown(
            f'<div class="em-card em-squircle"><p style="color:{_lpG};margin:0;">'
            f"No generated assets yet for this client.</p></div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    _fil_a, _fil_b, _fil_c = st.columns(3)
    with _fil_a:
        _ap_pick = st.multiselect(
            "Approval stage",
            options=list(db.APPROVAL_STAGES),
            default=[],
            key=f"lib_fil_ap_{_cid}",
            help="Empty = all stages.",
        )
    with _fil_b:
        _qc_pick = st.multiselect(
            "QC status",
            options=list(db.QC_STATUSES),
            default=[],
            key=f"lib_fil_qc_{_cid}",
            help="Empty = all statuses.",
        )
    with _fil_c:
        _img_pick = st.selectbox(
            "Has final images",
            options=["All", "Has both finals", "Needs images"],
            index=0,
            key=f"lib_fil_img_{_cid}",
        )
    _fmt_pick = st.multiselect(
        "Post format",
        options=list(POST_FORMAT_OPTIONS),
        default=[],
        key=f"lib_fil_fmt_{_cid}",
        help="Empty = all formats (Feed, Story, Short Video).",
    )
    _img_mode = _img_pick if _img_pick != "All" else ""
    posts = _filter_posts_for_library(
        posts_all,
        approval_pick=_ap_pick,
        qc_pick=_qc_pick,
        images_mode=_img_mode,
        format_pick=_fmt_pick,
    )
    if not posts:
        st.info("No posts match these filters — adjust filters above or clear selections.")

    if posts:
        _seq_map = db.client_post_sequence_by_id(int(client["id"]))
        _pids = [int(p["id"]) for p in posts]
        _bulk_ms = f"bulk_ms_{_cid}"
        _psel = st.session_state.get(_bulk_ms)
        if isinstance(_psel, list):
            _allowed = set(_pids)
            st.session_state[_bulk_ms] = [int(x) for x in _psel if int(x) in _allowed]
        _br1, _br2 = st.columns([1, 4])
        with _br1:
            _bsa, _bsb = st.columns(2)
            with _bsa:
                if st.button(
                    "Select all",
                    key=f"bulk_sa_{_cid}",
                    use_container_width=True,
                ):
                    st.session_state[_bulk_ms] = list(_pids)
                    st.rerun()
            with _bsb:
                if st.button(
                    "Deselect all",
                    key=f"bulk_clear_{_cid}",
                    use_container_width=True,
                ):
                    st.session_state[_bulk_ms] = []
                    st.rerun()
        with _br2:
            st.multiselect(
                "Select posts for bulk actions",
                options=_pids,
                format_func=lambda i: f"Post #{_seq_map.get(int(i), '?')} · id {int(i)}",
                key=_bulk_ms,
                placeholder="Choose posts…",
            )
        _picked = [int(x) for x in (st.session_state.get(_bulk_ms) or [])]
        if _picked:
            st.markdown(
                f'<div class="em-card em-squircle" style="padding:14px 16px;margin-bottom:10px;">'
                f'<p style="color:{_lpW};font-weight:600;margin:0 0 6px 0;font-family:Georgia,serif;">'
                f"Bulk actions</p>"
                f'<p style="color:{_lpG};font-size:0.85rem;margin:0;">'
                f"{len(_picked)} post(s) selected</p></div>",
                unsafe_allow_html=True,
            )
            _ba1, _ba2, _ba3 = st.columns(3)
            with _ba1:
                if st.button(
                    "Mark ready for publisher",
                    key=f"bulk_ready_{_cid}",
                    use_container_width=True,
                    disabled=not role_ctx.user_can("bulk_ready_publisher"),
                ):
                    n = db.bulk_mark_ready_for_publisher(_cid, _picked)
                    _bump_gap_cache()
                    st.success(f"Marked {n} post(s) ready for the publisher queue.")
                    st.rerun()
            with _ba2:
                _stg_key = f"bulk_stg_{_cid}"
                st.selectbox(
                    "Set approval stage",
                    options=(
                        db.APPROVAL_INTERNAL_DRAFT,
                        db.APPROVAL_CLIENT_REVIEW,
                        db.APPROVAL_APPROVED,
                    ),
                    key=_stg_key,
                    disabled=not role_ctx.user_can("bulk_approval_stage"),
                )
                if st.button(
                    "Apply approval stage",
                    key=f"bulk_ap_{_cid}",
                    use_container_width=True,
                    disabled=not role_ctx.user_can("bulk_approval_stage"),
                ):
                    _st = str(st.session_state.get(_stg_key, db.APPROVAL_INTERNAL_DRAFT))
                    n = db.bulk_set_approval_stage(_cid, _picked, _st)
                    _bump_gap_cache()
                    st.success(f"Updated approval stage on {n} post(s).")
                    st.rerun()
            with _ba3:
                if st.button(
                    "Duplicate selected",
                    key=f"bulk_dup_{_cid}",
                    use_container_width=True,
                    disabled=not role_ctx.user_can("bulk_duplicate"),
                ):
                    new_ids = bulk_actions.duplicate_posts_for_client(_cid, _picked)
                    _bump_gap_cache()
                    st.success(
                        f"Created **{len(new_ids)}** draft duplicate(s). "
                        f"New post ids: {', '.join(str(x) for x in new_ids[:12])}"
                        f"{' …' if len(new_ids) > 12 else ''}"
                    )
                    st.rerun()
            _dok = f"bulk_del_ok_{_cid}"
            _dd1, _dd2 = st.columns([2, 1])
            with _dd1:
                st.checkbox(
                    "I understand these posts will be permanently deleted",
                    key=_dok,
                )
            with _dd2:
                if st.button(
                    "Delete selected",
                    key=f"bulk_del_{_cid}",
                    type="primary",
                    use_container_width=True,
                    disabled=not role_ctx.user_can("bulk_delete"),
                ):
                    if not st.session_state.get(_dok):
                        st.error("Confirm the checkbox above first.")
                    else:
                        n = db.delete_posts_for_client(_cid, _picked)
                        st.session_state[_bulk_ms] = []
                        st.session_state[_dok] = False
                        _bump_gap_cache()
                        st.toast(f"Deleted {n} post(s)", icon="🗑️")
                        st.rerun()

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
                    "approval": (_p.get("approval_stage") or "—")[:22],
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
    
            _img_sq = (row.get("image_prompt_square") or "").strip() or str(row.get("image_prompt") or "")
            _img_916 = (row.get("image_prompt_vertical") or "").strip() or str(row.get("image_prompt") or "")
            _k11 = f"gen_ed_11_{_cid}_{_pid}"
            _k916 = f"gen_ed_916_{_cid}_{_pid}"
            if _k11 not in st.session_state:
                st.session_state[_k11] = str(_img_sq)
            if _k916 not in st.session_state:
                st.session_state[_k916] = str(_img_916)
            _kvid = f"gen_ed_vid_{_cid}_{_pid}"
            if _kvid not in st.session_state:
                st.session_state[_kvid] = str(row.get("video_prompt") or "")
            _sq_disk = db.resolve_asset_path(str(row.get("image_square_path") or ""))
            _vt_disk = db.resolve_asset_path(str(row.get("image_vertical_path") or ""))
            _ov_raw = str(row.get("suggested_text_overlay") or "")
            _hd0, _ft0 = overlay_pil.parse_overlay_heading_footer(_ov_raw)
            _vid_store = str(row.get("video_prompt") or "").strip()
            _vp_badge = ""
            if _vid_store:
                _vp_badge = (
                    f'<span style="color:{_lpG};font-size:0.82rem;margin-left:8px;">🎥 Video</span>'
                )
    
            st.markdown(
                f'<div class="em-card" style="margin-top:1.25rem;padding:1rem 1.1rem;">'
                f'<p style="color:{_lpG};font-size:0.85rem;margin:0 0 4px 0;">'
                f"Post #{_post_num} · {_ts_disp}{_vp_badge}</p>"
                f'<p style="color:{_lpW};font-weight:600;margin:0 0 12px 0;">Final previews</p></div>',
                unsafe_allow_html=True,
            )
            _pv_l, _pv_r = st.columns(2, gap="large")
            with _pv_l:
                if _sq_disk.is_file():
                    st.image(PILImage.open(_sq_disk), use_container_width=True, caption="Square (1:1) final")
                else:
                    st.caption("No square final on disk yet.")
            with _pv_r:
                if _vt_disk.is_file():
                    st.image(PILImage.open(_vt_disk), use_container_width=True, caption="Vertical (9:16) final")
                else:
                    st.caption("No vertical final on disk yet.")
            if _sq_disk.is_file() and _vt_disk.is_file():
                _dlx, _dly = st.columns(2)
                _sx = _sq_disk.suffix.lower() or ".jpg"
                _vx = _vt_disk.suffix.lower() or ".jpg"
                with _dlx:
                    st.download_button(
                        label="Download square final",
                        data=_sq_disk.read_bytes(),
                        file_name=f"post{_post_num}_square{_sx}",
                        mime="image/jpeg" if _sx in (".jpg", ".jpeg") else "image/png",
                        use_container_width=True,
                        key=f"dl_fs_{_cid}_{_pid}",
                    )
                with _dly:
                    st.download_button(
                        label="Download vertical final",
                        data=_vt_disk.read_bytes(),
                        file_name=f"post{_post_num}_vertical{_vx}",
                        mime="image/jpeg" if _vx in (".jpg", ".jpeg") else "image/png",
                        use_container_width=True,
                        key=f"dl_fv_{_cid}_{_pid}",
                    )
    
            st.text_area(
                "Caption",
                value=str(row["caption"]),
                height=min(220, 80 + len(str(row["caption"])) // 4),
                key=f"cap_ed_{_cid}_{_pid}",
                label_visibility="visible",
                disabled=not role_ctx.user_can("edit_caption"),
            )
            _cap_col_a, _cap_col_b = st.columns([1, 4])
            with _cap_col_a:
                if st.button(
                    "Save caption only",
                    key=f"save_cap_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("edit_caption"),
                ):
                    db.update_post_caption_only(
                        _pid,
                        str(st.session_state.get(f"cap_ed_{_cid}_{_pid}", "")),
                        note="Manual caption edit",
                    )
                    _bump_gap_cache()
                    st.success("Caption saved.")
                    st.rerun()
            with _cap_col_b:
                _clipboard_button("Copy caption", str(st.session_state.get(f"cap_ed_{_cid}_{_pid}", row["caption"])))
    
            st.markdown(
                f'<p style="color:{_lpW};font-weight:600;margin-top:1rem;">'
                f"AI image prompts (same idea — two crops)</p>"
                f'<p style="color:{_lpG};font-size:0.88rem;margin:0 0 8px 0;">'
                f"1:1 = feed / square · 9:16 = Stories / Reels — paste into Midjourney / Gemini / Imagen. "
                f"To <strong style=\"color:{_lpW};\">regenerate with Imagen</strong>, edit the prompts in "
                f"<strong style=\"color:{_lpW};\">Generate assets</strong> below (faster than copying from here).</p>",
                unsafe_allow_html=True,
            )
            _cp_sq, _cp_vt = st.columns(2)
            with _cp_sq:
                _clipboard_button(
                    "Copy 1:1 prompt",
                    str(st.session_state.get(_k11, _img_sq)),
                )
            with _cp_vt:
                _clipboard_button(
                    "Copy 9:16 prompt",
                    str(st.session_state.get(_k916, _img_916)),
                )
            _fmt_row = str(row.get("post_format") or "")
            if _vid_store:
                if video_prompts.is_short_video_format(_fmt_row) and role_ctx.user_can(
                    "edit_image_prompts"
                ):
                    st.caption(
                        "**Video prompt (Short Video)** — Edit the 9:16 motion brief in **Generate assets** below "
                        "(image prompts stay above). Caption edits follow your role."
                    )
                else:
                    st.markdown(
                        f'<p style="color:{_lpW};font-weight:600;margin-top:1rem;">Video prompt</p>'
                        f'<p style="color:{_lpG};font-size:0.88rem;margin:0 0 8px 0;">'
                        f"9:16 motion brief — read-only here; if this becomes Short Video, use **Generate assets**.</p>",
                        unsafe_allow_html=True,
                    )
                    st.text_area(
                        "Video prompt (read-only)",
                        value=_vid_store,
                        height=min(220, 80 + len(_vid_store) // 4),
                        key=f"vid_ro_{_cid}_{_pid}",
                        label_visibility="collapsed",
                        disabled=True,
                    )
                    _clipboard_button("Copy video prompt", _vid_store)

            _pk_ov = f"em_ov_pending_{_cid}_{_pid}"
            _can_pipe = role_ctx.user_can("full_asset_pipeline")
            with st.expander("Generate assets — Imagen + overlay", expanded=False):
                st.caption(
                    "In-app **baker**: edit 1:1 / 9:16 prompts below, then Imagen → optional overlay preview → "
                    "bake heading/footer → save **JPEG** finals (replaces the old copy-paste round trip)."
                )
                if not _can_pipe:
                    st.caption(
                        f"*{role_ctx.ROLE_LABEL_PRETTY.get(role_ctx.get_current_role(), 'This role')}:* "
                        "Imagen generation and overlay bake are disabled — prompts remain editable for handoff."
                    )
                st.text_area(
                    "1:1 — feed (square)",
                    height=min(200, 80 + len(str(st.session_state.get(_k11, ""))) // 5),
                    key=_k11,
                    label_visibility="visible",
                    disabled=not role_ctx.user_can("edit_image_prompts"),
                )
                st.text_area(
                    "9:16 — vertical (Stories)",
                    height=min(200, 80 + len(str(st.session_state.get(_k916, ""))) // 5),
                    key=_k916,
                    label_visibility="visible",
                    disabled=not role_ctx.user_can("edit_image_prompts"),
                )
                if video_prompts.is_short_video_format(_fmt_row):
                    st.checkbox(
                        "Generate Video Prompt",
                        value=True,
                        key=f"vv_gen_{_cid}_{_pid}",
                        help="Show the 9:16 motion brief field for Runway / Kling / Luma / Gemini Video. "
                        "Turn off to hide the field (still images unchanged). **Regenerate** runs the video "
                        "brief task only — no Imagen cost for stills.",
                        disabled=not role_ctx.user_can("edit_image_prompts"),
                    )
                    if st.session_state.get(f"vv_gen_{_cid}_{_pid}", True):
                        st.text_area(
                            "Video prompt (9:16 motion brief)",
                            height=min(
                                240,
                                100
                                + len(str(st.session_state.get(_kvid, ""))) // 5,
                            ),
                            key=_kvid,
                            label_visibility="visible",
                            disabled=not role_ctx.user_can("edit_image_prompts"),
                        )
                        _sv_a, _sv_b = st.columns(2)
                        with _sv_a:
                            if st.button(
                                "Save video prompt",
                                key=f"sv_save_{_cid}_{_pid}",
                                use_container_width=True,
                                disabled=not role_ctx.user_can("save_video_prompt_text"),
                            ):
                                db.update_post_video_prompt(
                                    _pid,
                                    str(st.session_state.get(_kvid, "")),
                                )
                                _bump_gap_cache()
                                st.success("Video prompt saved.")
                                st.rerun()
                        with _sv_b:
                            if st.button(
                                "Regenerate Video Prompt Only",
                                key=f"sv_reg_{_cid}_{_pid}",
                                use_container_width=True,
                                disabled=not role_ctx.user_can(
                                    "video_prompt_regenerate_crew"
                                ),
                            ):
                                try:
                                    _require_gemini()
                                    _fsv = _few_shot_captions_for_client(
                                        int(client["id"])
                                    )
                                    _nv = _run_video_prompt_regenerate(
                                        client, row, few_shot=_fsv
                                    )
                                    db.update_post_video_prompt(_pid, _nv)
                                    st.session_state[_kvid] = _nv
                                    _bump_gap_cache()
                                    st.success("Video prompt regenerated.")
                                    st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    st.error(str(exc))
                st.text_input(
                    "Overlay heading",
                    value=_hd0,
                    key=f"ov_h_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("edit_image_prompts"),
                )
                st.text_input(
                    "Overlay footer",
                    value=_ft0,
                    key=f"ov_f_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("edit_image_prompts"),
                )
                st.slider(
                    "Imagen guidance (0 = API default)",
                    0.0,
                    20.0,
                    0.0,
                    0.5,
                    key=f"ig_g_{_cid}_{_pid}",
                    disabled=not _can_pipe,
                )
                st.number_input(
                    "Optional Imagen seed (0 = random)",
                    min_value=0,
                    max_value=2_147_483_647,
                    value=0,
                    step=1,
                    key=f"ig_seed_{_cid}_{_pid}",
                    help="Same seed + same prompts reuses the cached Imagen pair for one hour.",
                    disabled=not _can_pipe,
                )
                st.checkbox(
                    "Review overlay preview first",
                    value=False,
                    key=f"ov_rev_{_cid}_{_pid}",
                    disabled=not _can_pipe,
                )
                _pend = st.session_state.get(_pk_ov)
                if _pend is not None:
                    st.info("Preview ready — adjust heading/footer if needed, then bake.")
                    _ppc1, _ppc2 = st.columns(2)
                    with _ppc1:
                        st.image(_pend["psq"], caption="Preview — square")
                    with _ppc2:
                        st.image(_pend["pvt"], caption="Preview — vertical")
                    _bclr1, _bclr2 = st.columns(2)
                    with _bclr1:
                        if st.button(
                            "Bake JPEGs & save to post",
                            type="primary",
                            use_container_width=True,
                            key=f"ov_bake_{_cid}_{_pid}",
                            disabled=not _can_pipe,
                        ):
                            try:
                                _h_b = str(st.session_state.get(f"ov_h_{_cid}_{_pid}", ""))
                                _f_b = str(st.session_state.get(f"ov_f_{_cid}_{_pid}", ""))
                                jsq, jvt = asset_pipeline.run_full_bake_jpeg(
                                    _pend["raw_sq"],
                                    _pend["raw_vt"],
                                    _h_b,
                                    _f_b,
                                )
                                db.save_post_final_assets(
                                    int(client["id"]),
                                    _pid,
                                    jsq,
                                    jvt,
                                    square_suffix=".jpg",
                                    vertical_suffix=".jpg",
                                )
                                _bump_gap_cache()
                                st.session_state.pop(_pk_ov, None)
                                st.success("JPEG finals saved.")
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                logger.exception("Overlay bake / save failed")
                                st.error(str(exc))
                    with _bclr2:
                        if st.button(
                            "Discard preview",
                            use_container_width=True,
                            key=f"ov_disc_{_cid}_{_pid}",
                            disabled=not _can_pipe,
                        ):
                            st.session_state.pop(_pk_ov, None)
                            st.rerun()
                if st.button(
                    "Generate both images + apply overlay",
                    type="primary",
                    use_container_width=True,
                    key=f"ov_go_{_cid}_{_pid}",
                    disabled=_pend is not None or not _can_pipe,
                ):
                    try:
                        _require_gemini()
                        _gs = asset_pipeline.guidance_config_value(
                            float(st.session_state.get(f"ig_g_{_cid}_{_pid}", 0.0))
                        )
                        _h_run = str(st.session_state.get(f"ov_h_{_cid}_{_pid}", ""))
                        _f_run = str(st.session_state.get(f"ov_f_{_cid}_{_pid}", ""))
                        _do_prev = bool(st.session_state.get(f"ov_rev_{_cid}_{_pid}", False))
                        _sq_run = str(st.session_state.get(_k11, _img_sq)).strip()
                        _vt_run = str(st.session_state.get(_k916, _img_916)).strip()
                        _seed_raw = int(st.session_state.get(f"ig_seed_{_cid}_{_pid}", 0) or 0)
                        _seed_use = None if _seed_raw <= 0 else _seed_raw
                        with st.status("Generating images with Imagen…", expanded=True) as _st:
                            _st.write("Calling Imagen for 1:1 and 9:16…")
                            raw_sq, raw_vt = asset_pipeline.generate_imagen_cached(
                                int(client["id"]),
                                _pid,
                                _sq_run,
                                _vt_run,
                                _gs,
                                _seed_use,
                            )
                            _st.write("Imagen complete.")
                        if _do_prev:
                            psq, pvt = asset_pipeline.run_preview_then_bake(
                                raw_sq, raw_vt, _h_run, _f_run
                            )
                            st.session_state[_pk_ov] = {
                                "raw_sq": raw_sq,
                                "raw_vt": raw_vt,
                                "psq": psq,
                                "pvt": pvt,
                            }
                            st.rerun()
                        with st.status("Baking overlay and saving JPEGs…", expanded=True) as _st2:
                            _st2.write("Compositing heading/footer…")
                            jsq, jvt = asset_pipeline.run_full_bake_jpeg(
                                raw_sq, raw_vt, _h_run, _f_run
                            )
                            _st2.write("Writing files…")
                        db.save_post_final_assets(
                            int(client["id"]),
                            _pid,
                            jsq,
                            jvt,
                            square_suffix=".jpg",
                            vertical_suffix=".jpg",
                        )
                        _bump_gap_cache()
                        st.success("JPEG finals saved — scroll up to preview.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Full asset generation failed")
                        st.error(str(exc))
    
            _upload_ok = role_ctx.user_can("upload_final_assets")
            st.markdown(
                f'<p style="color:{_lpW};font-weight:600;margin-top:1.25rem;">'
                f"Final images (manual upload)</p>"
                f'<p style="color:{_lpG};font-size:0.88rem;margin:0 0 8px 0;">'
                f"Optional: upload if you export outside this console. "
                f"Mark <strong>Ready for Publisher</strong> when QC passes.</p>",
                unsafe_allow_html=True,
            )
            if not _upload_ok:
                st.caption("Uploads are restricted for your role.")
            _qc = str(row.get("qc_status") or db.QC_STATUS_DRAFT)
            if _qc not in db.QC_STATUSES:
                _qc = db.QC_STATUS_DRAFT
            st.caption(f"QC status: **{_qc}**")
            _u1, _u2 = st.columns(2)
            with _u1:
                up_sq = st.file_uploader(
                    "Square file",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"fu_sq_{_cid}_{_pid}",
                    disabled=not _upload_ok,
                )
            with _u2:
                up_vt = st.file_uploader(
                    "Vertical file",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"fu_vt_{_cid}_{_pid}",
                    disabled=not _upload_ok,
                )
            _save_col, _rdy_col, _rev_col = st.columns(3)
            with _save_col:
                if st.button(
                    "Save final images",
                    key=f"save_final_{_cid}_{_pid}",
                    use_container_width=True,
                    disabled=not _upload_ok,
                ):
                    if up_sq is None or up_vt is None:
                        st.error("Upload both square and vertical files before saving.")
                    else:
                        _b_sq = up_sq.getvalue()
                        _b_vt = up_vt.getvalue()
                        try:
                            _im_sq = PILImage.open(io.BytesIO(_b_sq))
                            _w_sq, _h_sq = _im_sq.size
                            if _h_sq > 0 and abs((_w_sq / _h_sq) - 1.0) > 0.14:
                                st.warning(
                                    "Square file aspect ratio is not close to **1:1** — check crop before publishing."
                                )
                            _im_vt = PILImage.open(io.BytesIO(_b_vt))
                            _w_vt, _h_vt = _im_vt.size
                            if _h_vt > 0 and abs((_w_vt / _h_vt) - (9 / 16)) > 0.12:
                                st.warning(
                                    "Vertical file aspect ratio is not close to **9:16** — check crop before publishing."
                                )
                        except Exception:  # noqa: BLE001
                            st.warning("Could not read image dimensions for aspect check.")
                        _suf_sq = Path(up_sq.name).suffix.lower() or ".png"
                        _suf_vt = Path(up_vt.name).suffix.lower() or ".png"
                        db.save_post_final_assets(
                            int(client["id"]),
                            _pid,
                            _b_sq,
                            _b_vt,
                            square_suffix=_suf_sq,
                            vertical_suffix=_suf_vt,
                        )
                        _bump_gap_cache()
                        st.success("Final images saved.")
                        st.rerun()
            _has_both = _sq_disk.is_file() and _vt_disk.is_file()
            with _rdy_col:
                if st.button(
                    "Mark ready for publisher",
                    key=f"qc_ready_{_cid}_{_pid}",
                    use_container_width=True,
                    disabled=not _has_both
                    or _qc == db.QC_STATUS_READY
                    or not role_ctx.user_can("qc_mark_ready"),
                ):
                    db.set_post_qc_ready(_pid)
                    _bump_gap_cache()
                    st.success("Marked ready — visible on publisher link.")
                    st.rerun()
            with _rev_col:
                if st.button(
                    "Revert QC to draft",
                    key=f"qc_draft_{_cid}_{_pid}",
                    use_container_width=True,
                    disabled=_qc == db.QC_STATUS_DRAFT
                    or not role_ctx.user_can("qc_mark_ready"),
                ):
                    db.set_post_qc_draft(_pid)
                    _bump_gap_cache()
                    st.info("Reverted to draft (hidden from publisher queue).")
                    st.rerun()
    
            _cur_ast = (row.get("approval_stage") or db.APPROVAL_INTERNAL_DRAFT).strip()
            if _cur_ast not in db.APPROVAL_STAGES:
                _cur_ast = db.APPROVAL_INTERNAL_DRAFT
            _ix_ap = db.APPROVAL_STAGES.index(_cur_ast)
            with st.expander("Tools — caption, Imagen, client review, versions", expanded=False):
                _ap_sel = st.selectbox(
                    "Approval stage",
                    options=list(db.APPROVAL_STAGES),
                    index=_ix_ap,
                    key=f"ap_stage_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("save_approval_stage"),
                )
                if st.button(
                    "Save approval stage",
                    key=f"sv_ap_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("save_approval_stage"),
                ):
                    _sel_ap = st.session_state.get(f"ap_stage_{_cid}_{_pid}", _ap_sel)
                    db.update_post_approval_stage(_pid, str(_sel_ap))
                    _bump_gap_cache()
                    st.success("Approval stage saved.")
                    st.rerun()
                _tok = db.ensure_client_review_token(_pid)
                _base = (os.getenv("PUBLIC_APP_URL") or "").strip()
                _link = (
                    f"{_base}?view=client_review&token={_tok}"
                    if _base
                    else f"/?view=client_review&token={_tok}"
                )
                st.caption("Client review link (share read-only)")
                st.code(_link, language="text")
                if st.button(
                    "Regenerate caption only",
                    key=f"rcap_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("edit_caption"),
                ):
                    try:
                        _fs = _few_shot_captions_for_client(int(client["id"]))
                        _new_cap = _run_caption_only_regenerate(client, row, few_shot=_fs)
                        db.update_post_caption_only(_pid, _new_cap, note="Caption regenerate")
                        _bump_gap_cache()
                        st.success("Caption updated.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
                if st.button(
                    "Duplicate this post",
                    key=f"dup_post_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("duplicate_post"),
                ):
                    try:
                        _new_id = db.duplicate_post(_pid)
                        _bump_gap_cache()
                        st.success(f"Draft duplicate created (post id **{_new_id}**). Scroll the library to open it.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
                if st.button(
                    "Refresh AI Insights for this pillar/hook",
                    key=f"ai_ins_refresh_{_cid}_{_pid}",
                    disabled=not role_ctx.user_can("tools_ai_insights_refresh"),
                ):
                    st.session_state[f"ai_learn_snap_{_cid}_{_pid}"] = (
                        engagement_learner.build_performance_summary(
                            int(client["id"]),
                            focus_pillar=str(row.get("content_pillar") or ""),
                            focus_creative_hook=str(row.get("creative_hook") or ""),
                        )
                    )
                with st.expander(
                    "Performance insights (refreshed snapshot)",
                    expanded=False,
                ):
                    _snap = st.session_state.get(f"ai_learn_snap_{_cid}_{_pid}")
                    if not _snap:
                        st.caption(
                            "Click Refresh AI Insights above to compute a snapshot for this "
                            "post's pillar and hook (falls back to account-wide when slice is thin)."
                        )
                    else:
                        if _snap.get("scope_note"):
                            st.caption(str(_snap["scope_note"]))
                        st.caption(f"Computed: {_snap.get('computed_at', '—')}")
                        if _snap.get("insufficient_data_message"):
                            st.info(str(_snap["insufficient_data_message"]))
                        for _ln in _snap.get("winning_patterns") or []:
                            st.markdown(
                                f"<p style='margin:4px 0;line-height:1.45;'>{html.escape(str(_ln))}</p>",
                                unsafe_allow_html=True,
                            )
                        _hp2 = _snap.get("recent_high_performers") or []
                        if _hp2:
                            st.markdown(
                                f'<p style="color:{_lpW};font-weight:600;margin:10px 0 4px 0;">'
                                f"Standouts (like-rate)</p>",
                                unsafe_allow_html=True,
                            )
                            st.dataframe(
                                pd.DataFrame(_hp2),
                                use_container_width=True,
                                hide_index=True,
                            )
                st.caption(
                    "Separate 1:1 / 9:16 Imagen buttons use the **prompts** and **Imagen guidance** from "
                    "**Generate assets** above — prefer the **Generate assets** baker for the full pair + overlay."
                )
                _gs_tool = asset_pipeline.guidance_config_value(
                    float(st.session_state.get(f"ig_g_{_cid}_{_pid}", 0.0))
                )
                _sq_tool = str(st.session_state.get(_k11, _img_sq)).strip()
                _vt_tool = str(st.session_state.get(_k916, _img_916)).strip()
                _ig1, _ig2 = st.columns(2)
                with _ig1:
                    if st.button(
                        "Generate 1:1 (Imagen)",
                        key=f"im11_{_cid}_{_pid}",
                        disabled=not role_ctx.user_can("run_imagen"),
                    ):
                        try:
                            _require_gemini()
                            _bytes = image_generation.generate_imagen_png_bytes(
                                _sq_tool,
                                aspect_ratio="1:1",
                                guidance_scale=_gs_tool,
                            )
                            db.save_post_single_final_asset(
                                int(client["id"]),
                                _pid,
                                _bytes,
                                asset="square",
                            )
                            _bump_gap_cache()
                            st.success("Square asset saved.")
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
                with _ig2:
                    if st.button(
                        "Generate 9:16 (Imagen)",
                        key=f"im916_{_cid}_{_pid}",
                        disabled=not role_ctx.user_can("run_imagen"),
                    ):
                        try:
                            _require_gemini()
                            _bytes = image_generation.generate_imagen_png_bytes(
                                _vt_tool,
                                aspect_ratio="9:16",
                                guidance_scale=_gs_tool,
                            )
                            db.save_post_single_final_asset(
                                int(client["id"]),
                                _pid,
                                _bytes,
                                asset="vertical",
                            )
                            _bump_gap_cache()
                            st.success("Vertical asset saved.")
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
                _ov_prev = row.get("suggested_text_overlay") or ""
                _hd, _ft = overlay_pil.parse_overlay_heading_footer(_ov_prev)
                if _sq_disk.is_file() and _hd and _ft:
                    st.caption("Overlay bake preview (PIL — square on disk)")
                    try:
                        _preview = overlay_pil.bake_text_overlay(
                            _sq_disk.read_bytes(),
                            _hd,
                            _ft,
                            mode="preview",
                        )
                        st.image(_preview)
                    except Exception as exc:  # noqa: BLE001
                        st.caption(f"Preview failed: {exc}")
                _vers = db.get_post_versions(_pid)
                if _vers:
                    st.caption("Version history")
                    st.dataframe(pd.DataFrame(_vers), use_container_width=True, hide_index=True)
    
            if _ov_raw:
                with st.expander("Suggested text overlay (JSON)", expanded=False):
                    try:
                        st.json(json.loads(_ov_raw))
                    except json.JSONDecodeError:
                        st.text(_ov_raw)
    
            _meta = []
            if (row.get("content_pillar") or "").strip():
                _meta.append(f"Pillar · **{html.escape(row['content_pillar'])}**")
            if (row.get("featured_brand") or "").strip():
                _meta.append(f"Brand · **{html.escape(row['featured_brand'])}**")
            if (row.get("post_format") or "").strip():
                _meta.append(f"Format · **{html.escape(row['post_format'])}**")
            if _meta:
                st.markdown(
                    f"<p style='color:{_lpG};font-size:0.9rem;margin-top:12px;'>"
                    + " &nbsp;|&nbsp; ".join(_meta)
                    + "</p>",
                    unsafe_allow_html=True,
                )
    
            st.selectbox(
                "Delivery status",
                options=list(db.WORKFLOW_STATUSES),
                key=_wk,
                on_change=_make_workflow_change_handler(_pid, _wk),
                disabled=not role_ctx.user_can("edit_workflow_status"),
            )
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
