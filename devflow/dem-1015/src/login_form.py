"""Login form state machine wiring validation, auth adapter and a11y states.

This is where every interactive acceptance criterion lands: field errors with
aria state (AC-003/004), password visibility toggle (AC-005), loading + duplicate
submit prevention (AC-006), unified 401 copy (AC-007) and safe redirect (AC-008).

The auth adapter is injected via the constructor (the dependency-injection seam
called out as a P1 review finding), so tests can swap in deterministic doubles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .auth import AuthAdapter, AuthErrorCode, AuthResult, Credentials
from .i18n import get_message
from .security import resolve_redirect
from .validation import validate_form


@dataclass
class FieldState:
    """Accessibility + validation state for a single form field."""

    value: str = ""
    invalid: bool = False
    error_key: Optional[str] = None
    described_by: Optional[str] = None

    @property
    def error_message(self) -> str:
        """Return the localized error text for this field (empty when valid)."""
        return get_message(self.error_key) if self.error_key else ""


def _map_error(error_code: Optional[str]) -> str:
    """Map a normalized error code to a user-facing message key.

    The 401 case maps to the unified ``invalid_credentials`` copy so the page
    never reveals whether the account exists (AC-DEM-1015-007).
    """
    if error_code == AuthErrorCode.INVALID_CREDENTIALS:
        return "invalid_credentials"
    if error_code == AuthErrorCode.RATE_LIMITED:
        return "rate_limited"
    if error_code == AuthErrorCode.ACCOUNT_LOCKED:
        return "account_locked"
    if error_code in (AuthErrorCode.NETWORK_ERROR, AuthErrorCode.TIMEOUT):
        return "network_error"
    return "server_error"


@dataclass
class LoginForm:
    """Login form state machine (inject an :class:`AuthAdapter`)."""

    auth_adapter: AuthAdapter
    _account: FieldState = field(default_factory=FieldState)
    _password: FieldState = field(default_factory=FieldState)
    _password_visible: bool = False
    _loading: bool = False
    _form_error_key: Optional[str] = None
    _last_result: Optional[AuthResult] = None
    _pending_redirect: Optional[str] = None

    # ---- password visibility -------------------------------------------------
    def toggle_password_visibility(self) -> bool:
        """Flip password visibility and return the new visible state."""
        self._password_visible = not self._password_visible
        return self._password_visible

    @property
    def password_input_type(self) -> str:
        """Return ``text`` when the password is visible, else ``password``."""
        return "text" if self._password_visible else "password"

    @property
    def password_aria_pressed(self) -> bool:
        """Return the aria-pressed state synced with visibility."""
        return self._password_visible

    # ---- field states ---------------------------------------------------------
    @property
    def account(self) -> FieldState:
        return self._account

    @property
    def password(self) -> FieldState:
        return self._password

    @property
    def account_aria_invalid(self) -> bool:
        return self._account.invalid

    @property
    def password_aria_invalid(self) -> bool:
        return self._password.invalid

    # ---- loading / submission ------------------------------------------------
    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def submit_disabled(self) -> bool:
        return self._loading

    @property
    def submit_status_text(self) -> str:
        """Return screen-reader status text while submitting."""
        return get_message("submitting") if self._loading else ""

    @property
    def form_error_message(self) -> str:
        return get_message(self._form_error_key) if self._form_error_key else ""

    @property
    def form_error_alert_role(self) -> str:
        """Return ``alert`` when a form-level error is present (role=alert)."""
        return "alert" if self._form_error_key else ""

    @property
    def pending_redirect(self) -> Optional[str]:
        return self._pending_redirect

    # ---- behaviour -----------------------------------------------------------
    def submit_on_enter(self, source_field: str) -> bool:
        """Return True when pressing Enter in ``source_field`` should submit."""
        return source_field in ("account", "password")

    def submit(self, account: str, password: str) -> Optional[AuthResult]:
        """Validate then submit; returns None on validation failure or duplicate click.

        While loading, any further submit is ignored so a repeat click never
        triggers a second request (AC-DEM-1015-006).
        """
        self._account.value = account
        self._password.value = password
        if self._loading:
            return None
        validation = validate_form(account, password)
        self._account.invalid = validation.account_error is not None
        self._password.invalid = validation.password_error is not None
        self._account.error_key = validation.account_error
        self._password.error_key = validation.password_error
        self._account.described_by = "account-error" if validation.account_error else None
        self._password.described_by = "password-error" if validation.password_error else None
        if not validation.is_valid:
            return None
        self._loading = True
        try:
            result = self.auth_adapter.login(Credentials(account=account, password=password))
        finally:
            self._loading = False
        self._last_result = result
        if result.success:
            self._form_error_key = None
            self._pending_redirect = resolve_redirect(result.redirect)
        else:
            self._form_error_key = _map_error(result.error_code)
        return result
