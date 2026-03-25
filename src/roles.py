"""
Lightweight role model: URL ?role= + session (no password auth).

Roles: admin, copywriter, designer, publisher.
"""

from __future__ import annotations

import streamlit as st

EM_ROLE_SESSION_KEY = "em_role"

ROLE_ADMIN = "admin"
ROLE_COPYWRITER = "copywriter"
ROLE_DESIGNER = "designer"
ROLE_PUBLISHER = "publisher"

VALID_ROLES: tuple[str, ...] = (
    ROLE_ADMIN,
    ROLE_COPYWRITER,
    ROLE_DESIGNER,
    ROLE_PUBLISHER,
)

# Must match app.py VIEW_* string values.
VIEW_DASHBOARD = "Dashboard"
VIEW_ONBOARD = "New client"
VIEW_OVERLAY = "Overlay studio"
VIEW_ANALYTICS = "Analytics"
VIEW_CONTENT_CALENDAR = "Content Calendar"

ROLE_LABEL_PRETTY: dict[str, str] = {
    ROLE_ADMIN: "Admin",
    ROLE_COPYWRITER: "Copywriter",
    ROLE_DESIGNER: "Designer",
    ROLE_PUBLISHER: "Publisher",
}


def normalize_role(raw: str | None) -> str:
    if not raw:
        return ROLE_ADMIN
    r = str(raw).strip().lower()
    if r in VALID_ROLES:
        return r
    return ROLE_ADMIN


def init_role_from_query_params(*, publisher_view: bool) -> None:
    """
    Call once per run after ``set_page_config``.

    Publisher queue URL forces ``publisher``. Otherwise ``?role=`` overrides session;
    default session role is ``admin``.
    """
    if publisher_view:
        st.session_state[EM_ROLE_SESSION_KEY] = ROLE_PUBLISHER
        return
    raw = st.query_params.get("role")
    if raw:
        st.session_state[EM_ROLE_SESSION_KEY] = normalize_role(str(raw))
    elif EM_ROLE_SESSION_KEY not in st.session_state:
        st.session_state[EM_ROLE_SESSION_KEY] = ROLE_ADMIN


# Session keys cleared when admin switches role (avoids stale hub / hotkey state).
VOLATILE_SESSION_KEYS_ON_ROLE_CHANGE: tuple[str, ...] = (
    "em_pending_autopilot",
    "em_gen_progress",
    "_hotkey_run_pipeline",
)


def clear_volatile_session_after_role_change() -> None:
    """Pop one-shot generation keys so widgets stay consistent after role switch."""
    for k in VOLATILE_SESSION_KEYS_ON_ROLE_CHANGE:
        st.session_state.pop(k, None)


def get_current_role() -> str:
    return normalize_role(st.session_state.get(EM_ROLE_SESSION_KEY))


def filter_sidebar_views_for_role(role: str | None = None) -> list[str]:
    """Sorted list of allowed views (same as ``allowed_sidebar_views``, for docs/UI)."""
    return sorted(allowed_sidebar_views(role))


def allowed_sidebar_views(role: str | None = None) -> frozenset[str]:
    """Which main ``current_view`` values the role may use."""
    r = normalize_role(role) if role is not None else get_current_role()
    if r == ROLE_ADMIN:
        return frozenset(
            {
                VIEW_DASHBOARD,
                VIEW_ONBOARD,
                VIEW_OVERLAY,
                VIEW_ANALYTICS,
                VIEW_CONTENT_CALENDAR,
            }
        )
    if r == ROLE_COPYWRITER:
        return frozenset({VIEW_DASHBOARD, VIEW_ANALYTICS, VIEW_CONTENT_CALENDAR})
    if r == ROLE_DESIGNER:
        return frozenset({VIEW_DASHBOARD, VIEW_OVERLAY})
    if r == ROLE_PUBLISHER:
        return frozenset()
    return frozenset({VIEW_DASHBOARD})


def enforce_current_view_for_role() -> None:
    """If ``current_view`` is not allowed, reset to Dashboard and rerun."""
    allowed = allowed_sidebar_views()
    cv = st.session_state.get("current_view")
    if cv not in allowed:
        st.session_state["current_view"] = VIEW_DASHBOARD
        st.rerun()


# permission -> roles that may perform it (admin is always True in user_can)
_PERMISSION_ROLES: dict[str, frozenset[str]] = {
    "generate_crew": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "run_imagen": frozenset({ROLE_ADMIN, ROLE_DESIGNER}),
    "bake_overlay": frozenset({ROLE_ADMIN, ROLE_DESIGNER}),
    "full_asset_pipeline": frozenset({ROLE_ADMIN, ROLE_DESIGNER}),
    "edit_caption": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "edit_image_prompts": frozenset({ROLE_ADMIN, ROLE_COPYWRITER, ROLE_DESIGNER}),
    "view_analytics": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "view_calendar": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "view_overlay_studio": frozenset({ROLE_ADMIN, ROLE_DESIGNER}),
    "onboard_client": frozenset({ROLE_ADMIN}),
    "duplicate_post": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "upload_final_assets": frozenset({ROLE_ADMIN, ROLE_DESIGNER}),
    "qc_mark_ready": frozenset({ROLE_ADMIN, ROLE_DESIGNER}),
    "engagement_insights_toggle": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "gap_fill_generate": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "calendar_schedule": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "calendar_placeholder": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "video_prompt_regenerate_crew": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "critic_pass": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "edit_client_photography_style": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "bulk_duplicate": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "bulk_approval_stage": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "bulk_delete": frozenset({ROLE_ADMIN}),
    "bulk_ready_publisher": frozenset({ROLE_ADMIN, ROLE_COPYWRITER, ROLE_DESIGNER}),
    "tools_ai_insights_refresh": frozenset({ROLE_ADMIN, ROLE_COPYWRITER}),
    "save_approval_stage": frozenset({ROLE_ADMIN, ROLE_COPYWRITER, ROLE_DESIGNER}),
    "save_video_prompt_text": frozenset({ROLE_ADMIN, ROLE_COPYWRITER, ROLE_DESIGNER}),
    "edit_workflow_status": frozenset({ROLE_ADMIN, ROLE_COPYWRITER, ROLE_DESIGNER}),
}


def user_can(permission: str) -> bool:
    """Return True if the current role may perform ``permission``."""
    r = get_current_role()
    if r == ROLE_ADMIN:
        return True
    allowed_roles = _PERMISSION_ROLES.get(permission)
    if allowed_roles is None:
        return False
    return r in allowed_roles


def is_publisher_standalone() -> bool:
    return get_current_role() == ROLE_PUBLISHER
