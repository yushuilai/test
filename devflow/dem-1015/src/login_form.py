"""Login form state machine wiring validation, auth adapter and a11y states.

This is where every interactive acceptance criterion lands: field errors with
aria state (AC-003/004), password visibility toggle (AC-005), loading + duplicate
submit prevention (AC-006), unified failure copy (AC-007) and safe redirect
(AC-008).

Design notes fixed after independent verification:

* the auth adapter is injected through the constructor (the dependency-injection
  seam called out as a P1 review finding), so tests never depend on real I/O;
* every *new* submit clears the previous form-level error and pending redirect,
  otherwise a stale "账号或密码错误" or a stale navigation target survives into the
  next attempt (AC-008: a failed attempt must never navigate);
* the account is submitted trimmed, exactly as it was validated, so the value the
  backend sees matches the value that passed the format check.
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

    Both 401 and 423 collapse onto ``invalid_credentials``: a dedicated lockout
    message would confirm that the account exists and turn the form into an
    enumeration oracle. 429 (request rate) and 5xx (service health) leak nothing
    about the account, so they keep their own copy. Raw backend text is never
    surfaced.
    """
    if error_code in (AuthErrorCode.INVALID_CREDENTIALS, AuthErrorCode.ACCOUNT_LOCKED):
        return "invalid_credentials"
    if error_code == AuthErrorCode.RATE_LIMITED:
        return "rate_limited"
    if error_code in (AuthErrorCode.TIMEOUT, AuthErrorCode.NETWORK_ERROR):
        # A timeout and a dropped connection are indistinguishable to the user and
        # both mean "we do not know the outcome": one copy, no retry storm.
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
        """Flip password visibility and return the new visible state.

        Only the input ``type`` changes; the typed value is never touched
        (AC-DEM-1015-005).
        """
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

    @property
    def last_result(self) -> Optional[AuthResult]:
        return self._last_result

    # ---- behaviour -----------------------------------------------------------
    def submit_on_enter(self, source_field: str) -> bool:
        """Return True when pressing Enter in ``source_field`` should submit."""
        return source_field in ("account", "password")

    def submit(self, account: str, password: str) -> Optional[AuthResult]:
        """Validate then submit; returns None on validation failure or duplicate click.

        While loading, any further submit is ignored *before* mutating state, so a
        repeat click neither fires a second request nor wipes the in-flight
        status text (AC-DEM-1015-006).
        """
        if self._loading:
            return None

        normalized_account = account.strip()
        self._form_error_key = None
        self._pending_redirect = None
        self._account.value = normalized_account
        self._password.value = password

        validation = validate_form(normalized_account, password)
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
            result = self.auth_adapter.login(
                Credentials(account=normalized_account, password=password)
            )
        finally:
            self._loading = False

        self._last_result = result
        if result.success:
            self._form_error_key = None
            self._pending_redirect = resolve_redirect(result.redirect)
        else:
            self._form_error_key = _map_error(result.error_code)
        return result
