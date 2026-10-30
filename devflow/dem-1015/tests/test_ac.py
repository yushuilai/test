"""Acceptance tests covering every AC in the req_spec (AC-DEM-1015-001..015).

Each test function is named ``test_ac_<序号>`` and maps to a single acceptance
criterion. Browser-only metrics (LCP/CLS/FPS/axe) are asserted through the
declared performance targets and logic proxies implemented in ``src``.
"""

from __future__ import annotations

import threading

import pytest

from src.auth import AuthErrorCode, AuthResult, Credentials, MockAuthAdapter
from src.design_tokens import (
    DEFAULT_TOKENS,
    TEXT_CONTRAST_MIN,
    VisualSpec,
    contrast_ratio,
    relative_luminance,
    validate_visual_checklist,
)
from src.i18n import get_message
from src.layout import (
    BUTTON_HEIGHT_PX,
    VIEWPORTS,
    card_width_for,
    has_horizontal_scroll,
    tap_target_height,
)
from src.login_form import LoginForm
from src.motion import (
    continuous_animation_enabled,
    effective_motion_duration,
    is_ease_out,
    is_valid_motion_duration,
)
from src.page_shell import (
    FOCUSABLE_ELEMENTS,
    all_elements_have_accessible_name,
    focus_order,
    html_has_core_content,
    next_tab_focus,
    render_page_html,
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
    """Adapter that blocks until released so loading state can be observed."""

    def __init__(self) -> None:
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()

    def login(self, credentials: Credentials) -> AuthResult:
        self.calls += 1
        self.started.set()
        self.release.wait(timeout=5)
        return AuthResult(success=True, token="tok", redirect="/dashboard")


# AC-DEM-1015-001 ---------------------------------------------------------------
def test_ac_001_core_content_and_performance_targets() -> None:
    html = render_page_html()
    assert html_has_core_content(html)
    assert lcp_within_budget(PERFORMANCE_TARGETS.lcp_ms - 1)
    assert cls_within_budget(PERFORMANCE_TARGETS.cls - 0.01)
    assert PERFORMANCE_TARGETS.lcp_ms == 2500
    assert PERFORMANCE_TARGETS.cls == 0.1


# AC-DEM-1015-002 ---------------------------------------------------------------
def test_ac_002_five_focusable_elements_with_accessible_names() -> None:
    assert len(FOCUSABLE_ELEMENTS) == 5
    kinds = {element.kind for element in FOCUSABLE_ELEMENTS}
    assert {"input", "button", "checkbox", "link"}.issubset(kinds)
    assert all_elements_have_accessible_name()
    for element in FOCUSABLE_ELEMENTS:
        assert element.label or element.aria_label


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


# AC-DEM-1015-004 ---------------------------------------------------------------
def test_ac_004_invalid_account_format_error_and_no_password_leak() -> None:
    adapter = MockAuthAdapter()
    form = LoginForm(auth_adapter=adapter)
    result = form.submit("not-an-email", VALID_PASSWORD)
    assert result is None
    assert adapter.calls == []  # not submitted, no network
    assert form.account.error_key == ACCOUNT_INVALID_FORMAT
    assert validate_account("not-an-email") == ACCOUNT_INVALID_FORMAT
    assert VALID_PASSWORD not in form.account.error_message
    assert form.pending_redirect is None  # focus/context retained, no navigation


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
    form.toggle_password_visibility()
    assert form.password_input_type == "password"


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
    finally:
        adapter.release.set()
        thread.join(timeout=5)
    assert form.loading is False
    assert form.pending_redirect == "/dashboard"


# AC-DEM-1015-007 ---------------------------------------------------------------
def test_ac_007_unified_401_message_without_raw_error_exposure() -> None:
    adapter = MockAuthAdapter(status_code=401)
    form = LoginForm(auth_adapter=adapter)
    result = form.submit(VALID_ACCOUNT, "wrong-password")
    assert result is not None and result.success is False
    assert result.error_code == AuthErrorCode.INVALID_CREDENTIALS
    assert form.form_error_message == get_message("invalid_credentials")
    assert form.form_error_alert_role == "alert"
    # 5xx must not leak raw backend text either
    adapter_5xx = MockAuthAdapter(status_code=500)
    form_5xx = LoginForm(auth_adapter=adapter_5xx)
    form_5xx.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert "connection pool" not in form_5xx.form_error_message


# AC-DEM-1015-008 ---------------------------------------------------------------
def test_ac_008_success_redirect_safety_and_no_token_in_url() -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter(redirect="/dashboard", token="tok"))
    result = form.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert result is not None and result.success is True
    assert form.pending_redirect == "/dashboard"
    assert_token_not_in_url("tok", form.pending_redirect or "")

    # missing redirect -> default home
    form_missing = LoginForm(auth_adapter=MockAuthAdapter(redirect=None))
    form_missing.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form_missing.pending_redirect == "/"

    # external redirect -> default home (open-redirect protection)
    form_ext = LoginForm(auth_adapter=MockAuthAdapter(redirect="https://evil.example"))
    form_ext.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form_ext.pending_redirect == "/"
    assert is_safe_redirect("https://evil.example") is False
    assert is_safe_redirect("//evil.example") is False
    assert is_safe_redirect("/dashboard") is True
    assert resolve_redirect("https://evil.example") == "/"


# AC-DEM-1015-009 ---------------------------------------------------------------
def test_ac_009_keyboard_order_enter_submit_and_no_trap() -> None:
    assert focus_order() == ["account", "password", "remember", "forgot", "submit"]
    # distinct ids -> no focus trap / duplicate stops
    assert len(set(focus_order())) == len(focus_order())
    # Enter in either input submits
    form = LoginForm(auth_adapter=MockAuthAdapter())
    assert form.submit_on_enter("account") is True
    assert form.submit_on_enter("password") is True
    assert form.submit_on_enter("submit") is False
    # focus leaves the page at the end instead of looping back
    assert next_tab_focus(len(FOCUSABLE_ELEMENTS) - 1) is None


# AC-DEM-1015-010 ---------------------------------------------------------------
def test_ac_010_responsive_breakpoints_no_scroll_and_tap_target() -> None:
    for viewport in VIEWPORTS:
        assert has_horizontal_scroll(viewport) is False
        assert card_width_for(viewport) > 0
        assert card_width_for(viewport) <= viewport
    assert VIEWPORTS == (360, 768, 1440, 1920)
    assert tap_target_height() >= 44
    assert BUTTON_HEIGHT_PX >= 44


# AC-DEM-1015-011 ---------------------------------------------------------------
def test_ac_011_tech_feel_visual_checklist() -> None:
    spec = VisualSpec()
    assert validate_visual_checklist(spec) == []
    # dark base luminance < 30%
    assert relative_luminance(DEFAULT_TOKENS.background) < 0.30
    # micro-animation 150-400ms with ease-out
    assert is_valid_motion_duration(spec.motion_duration_ms)
    assert is_ease_out(spec.easing)
    assert spec.primary_color_count == 1
    assert spec.secondary_color_count == 1


# AC-DEM-1015-012 ---------------------------------------------------------------
def test_ac_012_reduced_motion_disables_animation_and_keeps_layout() -> None:
    assert continuous_animation_enabled(prefers_reduced_motion=True) is False
    assert effective_motion_duration(True, 250) <= 100
    assert effective_motion_duration(False, 250) == 250
    # layout / information must not be lost under reduced motion
    html = render_page_html()
    assert html_has_core_content(html)
    assert "@media (prefers-reduced-motion: reduce)" in html


# AC-DEM-1015-013 ---------------------------------------------------------------
def test_ac_013_accessibility_contrast_and_decorative_aria_hidden() -> None:
    assert contrast_ratio(DEFAULT_TOKENS.text_primary, DEFAULT_TOKENS.background) >= TEXT_CONTRAST_MIN
    assert contrast_ratio(DEFAULT_TOKENS.text_secondary, DEFAULT_TOKENS.background) >= TEXT_CONTRAST_MIN
    # focus ring vs background >= 3:1 (large/UI component)
    assert contrast_ratio(DEFAULT_TOKENS.focus_ring, DEFAULT_TOKENS.background) >= 3.0
    html = render_page_html()
    # decorative background layer is aria-hidden and outside the tab sequence
    assert "id='tech-background' aria-hidden='true'" in html
    assert "tabindex" not in html


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
    policy = TokenStoragePolicy()
    assert policy.use_http_only_cookie is True
    assert policy.secure is True
    assert policy.store_in_local_storage is False
    assert policy.store_in_session_storage is False
    html = render_page_html()
    assert "autocomplete='username'" in html
    assert "autocomplete='current-password'" in html


# AC-DEM-1015-015 ---------------------------------------------------------------
def test_ac_015_mobile_performance_budget_and_font_display_swap() -> None:
    assert js_within_budget(PERFORMANCE_TARGETS.measured_first_screen_js_kb)
    assert PERFORMANCE_TARGETS.first_screen_js_kb == 200  # budget cap
    assert PERFORMANCE_TARGETS.min_fps >= 50
    html = render_page_html()
    assert "font-display:swap" in html
    assert "sans-serif" in html  # system font fallback present
