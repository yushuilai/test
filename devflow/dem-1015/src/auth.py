"""Authentication adapter layer.

The single seam through which the login page talks to the backend. A mock
implementation provides every failure path (401/423/429/5xx/network/timeout) so
tests can inject them deterministically. This freezes the ``AuthAdapter``
contract raised as a P1 review finding (missing error surface / testability).

Token carrier: the contract defaults to an **HttpOnly cookie** (AC-008/AC-014
reconciliation). In that mode ``AuthResult.token`` is ``None`` because the
frontend must never be able to read the credential; only a hardened
``Set-Cookie`` string is surfaced. Memory-JWT mode is opt-in
(``cookie_mode=False``) and must be paired with a documented XSS risk
acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol


class AuthErrorCode:
    """Normalized error codes the form understands (never raw backend strings)."""

    INVALID_CREDENTIALS = "invalid_credentials"  # 401
    ACCOUNT_LOCKED = "account_locked"  # 423
    RATE_LIMITED = "rate_limited"  # 429
    SERVER_ERROR = "server_error"  # 5xx
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"


DEFAULT_SESSION_COOKIE = "session=mock-session-id; Path=/; HttpOnly; Secure; SameSite=Lax"


@dataclass(frozen=True)
class Credentials:
    """Credentials submitted by the user."""

    account: str
    password: str


@dataclass(frozen=True)
class AuthResult:
    """Normalized outcome of a login attempt.

    On success ``success`` is True and either ``session_cookie`` (HttpOnly mode)
    or ``token`` (memory-JWT mode) plus ``redirect`` are populated. On failure
    ``error_code`` identifies the kind of failure; ``raw_error`` may carry
    backend detail that must never reach the user message.
    """

    success: bool
    redirect: Optional[str] = None
    token: Optional[str] = None
    session_cookie: Optional[str] = None
    error_code: Optional[str] = None
    raw_error: Optional[str] = None


class AuthAdapter(Protocol):
    """Contract shared by the mock and any future real backend adapter."""

    def login(self, credentials: Credentials) -> AuthResult:
        """Attempt a login and return a normalized :class:`AuthResult`."""
        ...


class MockAuthAdapter:
    """Deterministic mock with configurable status, carrier and fault injection.

    ``calls`` records every ``login`` invocation so tests can assert that
    client-side validation and duplicate-submit guards really do suppress the
    request (AC-003/004/006).
    """

    def __init__(
        self,
        valid_account: str = "user@example.com",
        valid_password: str = "secret123",
        status_code: int = 200,
        redirect: Optional[str] = "/dashboard",
        token: str = "mock-access-token",
        session_cookie: str = DEFAULT_SESSION_COOKIE,
        cookie_mode: bool = True,
        raise_error: Optional[str] = None,
    ) -> None:
        self.valid_account = valid_account
        self.valid_password = valid_password
        self.status_code = status_code
        self.redirect = redirect
        self.token = token
        self.session_cookie = session_cookie
        self.cookie_mode = cookie_mode
        self.raise_error = raise_error
        self.calls: List[Credentials] = []

    def _success(self) -> AuthResult:
        """Build a success result honouring the configured token carrier."""
        if self.cookie_mode:
            return AuthResult(
                success=True, redirect=self.redirect, session_cookie=self.session_cookie
            )
        return AuthResult(success=True, redirect=self.redirect, token=self.token)

    def login(self, credentials: Credentials) -> AuthResult:
        """Record the call and return a result based on the configured scenario."""
        self.calls.append(credentials)
        if self.raise_error == "network":
            return AuthResult(success=False, error_code=AuthErrorCode.NETWORK_ERROR)
        if self.raise_error == "timeout":
            return AuthResult(success=False, error_code=AuthErrorCode.TIMEOUT)
        if (
            self.status_code == 200
            and credentials.account == self.valid_account
            and credentials.password == self.valid_password
        ):
            return self._success()
        if self.status_code == 200:
            return AuthResult(success=False, error_code=AuthErrorCode.INVALID_CREDENTIALS)
        if self.status_code == 401:
            return AuthResult(success=False, error_code=AuthErrorCode.INVALID_CREDENTIALS)
        if self.status_code == 423:
            return AuthResult(
                success=False,
                error_code=AuthErrorCode.ACCOUNT_LOCKED,
                raw_error="account locked after 5 failed attempts",
            )
        if self.status_code == 429:
            return AuthResult(
                success=False,
                error_code=AuthErrorCode.RATE_LIMITED,
                raw_error="rate limit exceeded for ip 10.0.0.7",
            )
        return AuthResult(
            success=False,
            error_code=AuthErrorCode.SERVER_ERROR,
            raw_error="internal server error: connection pool exhausted",
        )
