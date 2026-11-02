"""Acceptance tests covering every AC in the req_spec (AC-DEM-1015-001..015).

Each test function is named ``test_ac_<序号>`` and maps to a single acceptance
criterion. Browser-only metrics (LCP/CLS/FPS/axe) cannot be measured by pytest
without a real browser, so they are asserted through the declared budgets and the
logic proxies implemented in ``src``; the residual browser-only items are listed
in the self-test report rather than silently claimed as verified.
"""

from __future__ import annotations

import threading

import pytest

from src.auth import AuthErrorCode, AuthResult, Credentials, MockAuthAdapter
from src.design_tokens import (
    DEFAULT_TOKENS,
    LARGE_ICON_CONTRAST_MIN,
    TEXT_CONTRAST_MIN,
    VisualSpec,
    contrast_ratio,
    relative_luminance,
    validate_visual_checklist,
)
from src.i18n import get_message
from src.layout import (
    BUTTON_HEIGHT_PX,
    INPUT_HEIGHT_PX,
    SCROLL_PADDING_PX,
    TAP_TARGET_MIN_PX,
    VIEWPORTS,
    breakpoint_for,
    card_width_for,
    has_horizontal_scroll,
    is_input_occluded,
    is_tap_target_ok,
    scroll_padding_bottom,
    tap_target_height,
)
from src.login_form import LoginForm
from src.motion import (
    MOTION_MAX_MS,
    MOTION_MIN_MS,
    continuous_animation_enabled,
    effective_motion_duration,
    is_ease_out,
    is_valid_motion_duration,
)
from src.page_shell import (
    FOCUSABLE_ELEMENTS,
    REQUIRED_CONTROLS,
    all_elements_have_accessible_name,
    focus_order,
    html_has_aria_state_containers,
    html_has_core_content,
    next_tab_focus,
    render_page_html,
    required_control_ids,
)
from src.performance import (
    PERFORMANCE_TARGETS,
    cls_within_budget,
    js_within_budget,
    lcp_within_budget,
)
from src.security import (
    CredentialLeakError,
    TokenStoragePolicy,
    assert_no_credential_leak,
    assert_token_not_in_url,
    is_hardened_cookie,
    is_safe_redirect,
    resolve_redirect,
)
from src.validation import (
    ACCOUNT_INVALID_FORMAT,
    ACCOUNT_REQUIRED,
    PASSWORD_REQUIRED,
    validate_account,
    validate_password,
)

VALID_ACCOUNT = "user@example.com"
VALID_PASSWORD = "secret123"


class _SlowAdapter:
    """Adapter that blocks until released so the loading state can be observed."""

    def __init__(self) -> None:
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()

    def login(self, credentials: Credentials) -> AuthResult:
        self.calls += 1
        self.started.set()
        self.release.wait(timeout=5)
        return AuthResult(success=True, redirect="/dashboard", token="tok")


# AC-DEM-1015-001 ---------------------------------------------------------------
def test_ac_001_core_content_visible_and_performance_budget() -> None:
    html = render_page_html()
    assert html_has_core_content(html)
    assert "<h1>登录</h1>" in html
    assert lcp_within_budget(PERFORMANCE_TARGETS.lcp_ms - 1)
    assert cls_within_budget(PERFORMANCE_TARGETS.cls - 0.01)
    assert PERFORMANCE_TARGETS.lcp_ms == 2500
    assert PERFORMANCE_TARGETS.cls == 0.1
    assert PERFORMANCE_TARGETS.tbt_ms == 200


# AC-DEM-1015-002 ---------------------------------------------------------------
def test_ac_002_required_controls_present_with_accessible_names() -> None:
    # AC-002 enumerates five required controls.
    assert len(REQUIRED_CONTROLS) == 5
    kinds = {element.kind for element in REQUIRED_CONTROLS}
    assert {"input", "button", "checkbox", "link"}.issubset(kinds)
    assert all_elements_have_accessible_name(REQUIRED_CONTROLS)
    # Every required control is actually reachable in the tab sequence.
    stops = focus_order()
    for control_id in required_control_ids():
        assert control_id in stops
    assert all_elements_have_accessible_name()
    html = render_page_html()
    for control_id in required_control_ids():
        assert f"id='{control_id}'" in html


# AC-DEM-1015-003 ---------------------------------------------------------------
def test_ac_003_empty_submit_no_network_and_field_errors() -> None:
    adapter = MockAuthAdapter()
    form = LoginForm(auth_adapter=adapter)
    result = form.submit("", "")
    assert result is None
    assert adapter.calls == []  # no network request
    assert form.account_aria_invalid is True
    assert form.password_aria_invalid is True
    assert form.account.error_key == ACCOUNT_REQUIRED
    assert form.password.error_key == PASSWORD_REQUIRED
    assert form.account.described_by == "account-error"
    assert form.password.described_by == "password-error"
    assert form.account.error_message == get_message("account_required")
    html = render_page_html()
    assert "aria-describedby='account-error'" in html
    assert "aria-describedby='password-error'" in html
    assert html_has_aria_state_containers(html)


# AC-DEM-1015-004 ---------------------------------------------------------------
def test_ac_004_invalid_account_format_error_without_password_leak() -> None:
    adapter = MockAuthAdapter()
    form = LoginForm(auth_adapter=adapter)
    result = form.submit("not-an-email", VALID_PASSWORD)
    assert result is None
    assert adapter.calls == []  # not submitted, no network
    assert form.account.error_key == ACCOUNT_INVALID_FORMAT
    assert validate_account("not-an-email") == ACCOUNT_INVALID_FORMAT
    assert VALID_PASSWORD not in form.account.error_message
    assert form.pending_redirect is None  # focus/context retained, no navigation
    # the validated (trimmed) value is the submitted value
    trimmed = LoginForm(auth_adapter=MockAuthAdapter())
    trimmed.submit(f"  {VALID_ACCOUNT}  ", VALID_PASSWORD)
    assert trimmed.password.value == VALID_PASSWORD


# AC-DEM-1015-005 ---------------------------------------------------------------
def test_ac_005_password_visibility_toggle() -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter())
    assert form.password_input_type == "password"
    assert form.password_aria_pressed is False
    form.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form.password.value == VALID_PASSWORD
    assert form.toggle_password_visibility() is True
    assert form.password_input_type == "text"
    assert form.password_aria_pressed is True
    assert form.password.value == VALID_PASSWORD  # content preserved
    assert form.toggle_password_visibility() is False
    assert form.password_input_type == "password"
    html = render_page_html()
    assert "aria-pressed='false'" in html
    assert "type='button'" in html  # toggle must not submit the form


# AC-DEM-1015-006 ---------------------------------------------------------------
def test_ac_006_loading_disabled_and_duplicate_submit_prevention() -> None:
    adapter = _SlowAdapter()
    form = LoginForm(auth_adapter=adapter)
    thread = threading.Thread(target=form.submit, args=(VALID_ACCOUNT, VALID_PASSWORD))
    thread.start()
    adapter.started.wait(timeout=2)
    try:
        assert form.loading is True
        assert form.submit_disabled is True
        assert form.submit_status_text == get_message("submitting")
        second = form.submit(VALID_ACCOUNT, VALID_PASSWORD)  # duplicate click
        assert second is None
        assert adapter.calls == 1
        assert form.loading is True  # duplicate click did not disturb the request
    finally:
        adapter.release.set()
        thread.join(timeout=5)
    assert form.loading is False
    assert form.pending_redirect == "/dashboard"
    html = render_page_html()
    assert "aria-live" in html  # submitting status is exposed to screen readers


# AC-DEM-1015-007 ---------------------------------------------------------------
def test_ac_007_unified_failure_copy_without_raw_error_exposure() -> None:
    adapter = MockAuthAdapter(status_code=401)
    form = LoginForm(auth_adapter=adapter)
    result = form.submit(VALID_ACCOUNT, "wrong-password")
    assert result is not None and result.success is False
    assert result.error_code == AuthErrorCode.INVALID_CREDENTIALS
    assert form.form_error_message == get_message("invalid_credentials")
    assert form.form_error_alert_role == "alert"
    assert adapter.calls[0].account == VALID_ACCOUNT

    # 423 lockout must not confirm that the account exists (enumeration oracle).
    form_locked = LoginForm(auth_adapter=MockAuthAdapter(status_code=423))
    form_locked.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form_locked.form_error_message == get_message("invalid_credentials")
    assert "locked" not in form_locked.form_error_message.lower()

    # 5xx and 429 must not surface raw backend text.
    form_5xx = LoginForm(auth_adapter=MockAuthAdapter(status_code=500))
    form_5xx.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form_5xx.form_error_message == get_message("server_error")
    assert "connection pool" not in form_5xx.form_error_message

    form_429 = LoginForm(auth_adapter=MockAuthAdapter(status_code=429))
    form_429.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form_429.form_error_message == get_message("rate_limited")

    # timeout / offline both map to a network message, never to a raw exception.
    for mode in ("timeout", "network"):
        offline = LoginForm(auth_adapter=MockAuthAdapter(raise_error=mode))
        offline.submit(VALID_ACCOUNT, VALID_PASSWORD)
        assert offline.form_error_message
        assert offline.form_error_alert_role == "alert"

    assert "role='alert'" in render_page_html()


# AC-DEM-1015-008 ---------------------------------------------------------------
def test_ac_008_safe_redirect_and_token_never_in_url() -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter(redirect="/dashboard"))
    result = form.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert result is not None and result.success is True
    assert form.pending_redirect == "/dashboard"
    # HttpOnly cookie carrier: the frontend never holds the token value.
    assert result.token is None
    assert is_hardened_cookie(result.session_cookie) is True
    assert_token_not_in_url(result.token, form.pending_redirect or "")

    # missing redirect -> default home
    form_missing = LoginForm(auth_adapter=MockAuthAdapter(redirect=None))
    form_missing.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form_missing.pending_redirect == "/"

    # external / protocol-relative / backslash / control-char payloads -> default
    unsafe = [
        "https://evil.example",
        "//evil.example",
        "/\\evil.example",
        "/\\/evil.example",
        "/\t/evil.example",
        "/\n/evil.example",
    ]
    for payload in unsafe:
        assert is_safe_redirect(payload) is False, payload
        assert resolve_redirect(payload) == "/"
        hijacked = LoginForm(auth_adapter=MockAuthAdapter(redirect=payload))
        hijacked.submit(VALID_ACCOUNT, VALID_PASSWORD)
        assert hijacked.pending_redirect == "/"

    # legitimate same-site paths survive (fix must not be over-strict)
    for payload in ("/dashboard", "/a/b?x=1#h", "/"):
        assert resolve_redirect(payload) == payload
    assert resolve_redirect("  /dashboard") == "/dashboard"

    # a later failed attempt must clear the pending navigation target
    later = LoginForm(auth_adapter=MockAuthAdapter())
    later.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert later.pending_redirect == "/dashboard"
    later.submit(VALID_ACCOUNT, "wrong-password")
    assert later.pending_redirect is None


# AC-DEM-1015-009 ---------------------------------------------------------------
def test_ac_009_keyboard_order_enter_submit_and_no_trap() -> None:
    assert focus_order() == [
        "account",
        "password",
        "password-toggle",
        "remember",
        "forgot",
        "submit",
    ]
    assert len(set(focus_order())) == len(focus_order())  # no duplicate stops
    form = LoginForm(auth_adapter=MockAuthAdapter())
    assert form.submit_on_enter("account") is True
    assert form.submit_on_enter("password") is True
    assert form.submit_on_enter("submit") is False
    # focus leaves the page at the end instead of looping back
    assert next_tab_focus(len(FOCUSABLE_ELEMENTS) - 1) is None
    assert next_tab_focus(0) == 1
    with pytest.raises(IndexError):
        next_tab_focus(len(FOCUSABLE_ELEMENTS))
    # visible focus ring with >= 3:1 contrast against the page background
    assert contrast_ratio(DEFAULT_TOKENS.focus_ring, DEFAULT_TOKENS.background) >= 3.0


# AC-DEM-1015-010 ---------------------------------------------------------------
def test_ac_010_responsive_breakpoints_no_scroll_and_tap_target() -> None:
    assert VIEWPORTS == (360, 768, 1440, 1920)
    for viewport in VIEWPORTS:
        assert has_horizontal_scroll(viewport) is False
        assert 0 < card_width_for(viewport) <= viewport
    assert card_width_for(360) == 328  # 360 - 2 * 16 safe margin
    assert card_width_for(1920) == 420  # capped card width
    assert tap_target_height() >= TAP_TARGET_MIN_PX
    assert BUTTON_HEIGHT_PX >= 44
    assert is_tap_target_ok(INPUT_HEIGHT_PX) is True
    assert breakpoint_for(360) == "sm"
    assert breakpoint_for(1920) == "xl"
    # soft keyboard: the card must be scrollable so the focused input is not covered
    assert scroll_padding_bottom(300) >= 300
    assert scroll_padding_bottom(0) == SCROLL_PADDING_PX
    assert is_input_occluded(520, 640, 300) is True
    assert is_input_occluded(520, 640, 300, scroll_y=240) is False


# AC-DEM-1015-011 ---------------------------------------------------------------
def test_ac_011_tech_feel_visual_checklist() -> None:
    spec = VisualSpec()
    assert validate_visual_checklist(spec) == []
    assert relative_luminance(DEFAULT_TOKENS.background) < 0.30
    assert is_valid_motion_duration(spec.motion_duration_ms)
    assert MOTION_MIN_MS <= spec.motion_duration_ms <= MOTION_MAX_MS
    assert is_ease_out(spec.easing)
    assert spec.primary_color_count == 1
    assert spec.secondary_color_count == 1
    html = render_page_html()
    assert "backdrop-filter:blur" in html  # glassmorphism
    assert "animation:grid-drift" in html  # dynamic background layer
    assert "#submit:hover" in html and "#submit:active" in html and "#submit:focus-visible" in html

    # a broken checklist is detected instead of silently passing
    broken = VisualSpec(background_color="#FFFFFF", has_dynamic_background=False)
    assert "dark_base" in validate_visual_checklist(broken)
    assert "dynamic_background" in validate_visual_checklist(broken)


# AC-DEM-1015-012 ---------------------------------------------------------------
def test_ac_012_reduced_motion_disables_animation_and_keeps_layout() -> None:
    assert continuous_animation_enabled(prefers_reduced_motion=True) is False
    assert continuous_animation_enabled(prefers_reduced_motion=False) is True
    assert effective_motion_duration(True, 250) <= 100
    assert effective_motion_duration(False, 250) == 250
    html = render_page_html()
    assert "@media (prefers-reduced-motion: reduce)" in html
    assert "#tech-background::before{animation:none}" in html
    # layout / information must not be lost under reduced motion
    assert html_has_core_content(html)


# AC-DEM-1015-013 ---------------------------------------------------------------
def test_ac_013_accessibility_contrast_and_decorative_aria_hidden() -> None:
    assert contrast_ratio(DEFAULT_TOKENS.text_primary, DEFAULT_TOKENS.background) >= TEXT_CONTRAST_MIN
    assert contrast_ratio(DEFAULT_TOKENS.text_secondary, DEFAULT_TOKENS.background) >= TEXT_CONTRAST_MIN
    assert contrast_ratio(DEFAULT_TOKENS.focus_ring, DEFAULT_TOKENS.background) >= LARGE_ICON_CONTRAST_MIN
    html = render_page_html()
    # decorative background layer is aria-hidden and outside the tab sequence
    assert "id='tech-background' aria-hidden='true'" in html
    assert "tabindex" not in html
    assert html.count("aria-hidden='true'") >= 2  # background + decorative glyphs
    assert "aria-invalid='false'" in html
    assert "role='alert'" in html
    assert "aria-live='polite'" in html


# AC-DEM-1015-014 ---------------------------------------------------------------
def test_ac_014_no_credential_leak_and_token_storage_policy() -> None:
    password = VALID_PASSWORD
    assert_no_credential_leak(
        password=password,
        local_storage={},
        session_storage={},
        console_logs=[],
        url_query="",
    )
    with pytest.raises(CredentialLeakError):
        assert_no_credential_leak(
            password=password,
            local_storage={"k": password},
            session_storage={},
            console_logs=[],
            url_query="",
        )
    with pytest.raises(CredentialLeakError):
        assert_no_credential_leak(
            password=password,
            local_storage={},
            session_storage={"k": password},
            console_logs=["login " + password],
            url_query="",
        )
    with pytest.raises(CredentialLeakError):
        assert_token_not_in_url("tok", "/dashboard?token=tok")

    policy = TokenStoragePolicy()
    assert policy.use_http_only_cookie is True
    assert policy.secure is True
    assert policy.same_site == "Lax"
    assert policy.store_in_local_storage is False
    assert policy.store_in_session_storage is False

    result = LoginForm(auth_adapter=MockAuthAdapter()).submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert result is not None and result.token is None
    assert is_hardened_cookie(result.session_cookie)
    assert is_hardened_cookie("session=x; Path=/") is False

    html = render_page_html()
    assert "autocomplete='username'" in html
    assert "autocomplete='current-password'" in html
    # the page never persists credentials client-side
    assert "localStorage" not in html
    assert "sessionStorage" not in html


# AC-DEM-1015-015 ---------------------------------------------------------------
def test_ac_015_mobile_performance_budget_and_font_display_swap() -> None:
    assert js_within_budget(PERFORMANCE_TARGETS.measured_first_screen_js_kb)
    assert PERFORMANCE_TARGETS.first_screen_js_kb == 200  # budget cap
    assert js_within_budget(199) is True
    assert js_within_budget(200) is False
    assert PERFORMANCE_TARGETS.min_fps >= 50
    html = render_page_html()
    assert "font-display:swap" in html
    assert "sans-serif" in html  # system font fallback present
    assert len(html) < 64 * 1024  # single document, no framework payload


# Supplementary: validation regex parity with the rendered script --------------
def test_ac_004_domain_label_rules() -> None:
    for account in ("a@.com", "a@b..com", "a@b.", "a@b", "@example.com"):
        assert validate_account(account) == ACCOUNT_INVALID_FORMAT, account
    assert validate_account("  ") == ACCOUNT_REQUIRED
    assert validate_account(VALID_ACCOUNT) is None
    assert validate_password("") == PASSWORD_REQUIRED
    assert validate_password(" ") is None  # spaces are significant in passwords
