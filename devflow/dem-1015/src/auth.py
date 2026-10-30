"""Authentication adapter layer.

The single seam through which the login page talks to the backend. A mock
implementation provides every failure path (401/423/429/5xx/network/timeout) so
tests can inject them deterministically. This freezes the ``AuthAdapter``
contract raised as a P1 review finding (missing error surface / testability).
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


@dataclass(frozen=True)
class Credentials:
    """Credentials submitted by the user."""

    account: str
    password: str


@dataclass(frozen=True)
class AuthResult:
    """Normalized outcome of a login attempt.

    On success ``success`` is True and ``token``/``redirect`` are populated. On
    failure ``error_code`` identifies the kind of failure; ``raw_error`` may carry
    backend detail that must never reach the user message.
    """

    success: bool
    token: Optional[str] = None
    redirect: Optional[str] = None
    error_code: Optional[str] = None
    raw_error: Optional[str] = None


class AuthAdapter(Protocol):
    """Contract shared by the mock and any future real backend adapter."""

    def login(self, credentials: Credentials) -> AuthResult:
        """Attempt a login and return a normalized :class:`AuthResult`."""
        ...


class MockAuthAdapter:
    """Deterministic mock with configurable status, latency and fault injection."""

    def __init__(
        self,
        valid_account: str = "user@example.com",
        valid_password: str = "secret123",
        status_code: int = 200,
        redirect: str = "/dashboard",
        token: str = "mock-access-token",
        raise_error: Optional[str] = None,
    ) -> None:
        self.valid_account = valid_account
        self.valid_password = valid_password
        self.status_code = status_code
        self.redirect = redirect
        self.token = token
        self.raise_error = raise_error
        self.calls: List[Credentials] = []

    def login(self, credentials: Credentials) -> AuthResult:
        """Record the call and return a result based on the configured scenario."""
        self.calls.append(credentials)
        if self.raise_error == "network":
            return AuthResult(success=False, error_code=AuthErrorCode.NETWORK_ERROR)
        if self.raise_error == "timeout":
            return AuthResult(success=False, error_code=AuthErrorCode.TIMEOUT)
        if (
            credentials.account != self.valid_account
            or credentials.password != self.valid_password
        ):
            return AuthResult(success=False, error_code=AuthErrorCode.INVALID_CREDENTIALS)
        if self.status_code == 200:
            return AuthResult(success=True, token=self.token, redirect=self.redirect)
        if self.status_code == 401:
            return AuthResult(success=False, error_code=AuthErrorCode.INVALID_CREDENTIALS)
        if self.status_code == 423:
            return AuthResult(success=False, error_code=AuthErrorCode.ACCOUNT_LOCKED)
        if self.status_code == 429:
            return AuthResult(success=False, error_code=AuthErrorCode.RATE_LIMITED)
        return AuthResult(
            success=False,
            error_code=AuthErrorCode.SERVER_ERROR,
            raw_error="internal server error: connection pool exhausted",
        )
