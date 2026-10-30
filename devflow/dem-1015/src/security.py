"""Security helpers: safe redirect, token storage policy, credential-leak checks.

Implements the OWASP ASVS L1 login-related baseline: no credential/token in URL,
no token in client storage when an HttpOnly cookie is used, and open-redirect
protection on the post-login ``redirect`` parameter (AC-DEM-1015-008 / 014).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

DEFAULT_REDIRECT = "/"


def is_safe_redirect(redirect: Optional[str]) -> bool:
    """Return True only for same-site relative paths (no scheme / netloc / ``//``)."""
    if not redirect:
        return False
    target = redirect.strip()
    if not target.startswith("/"):
        return False
    if target.startswith("//"):
        return False
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return False
    return True


def resolve_redirect(redirect: Optional[str], default: str = DEFAULT_REDIRECT) -> str:
    """Resolve a post-login redirect, falling back to ``default`` when unsafe/missing."""
    if is_safe_redirect(redirect):
        return redirect
    return default


@dataclass(frozen=True)
class TokenStoragePolicy:
    """Declared storage strategy for the auth token.

    Defaults to an HttpOnly + Secure + SameSite cookie so the frontend never
    reads the token value and XSS cannot exfiltrate it (resolves the AC-008 /
    AC-014 token-carrier contradiction flagged in review).
    """

    use_http_only_cookie: bool = True
    secure: bool = True
    same_site: str = "Lax"
    store_in_local_storage: bool = False
    store_in_session_storage: bool = False


class CredentialLeakError(AssertionError):
    """Raised when a credential or token is found where it must not be."""


def assert_no_credential_leak(
    password: str,
    local_storage: Dict[str, str],
    session_storage: Dict[str, str],
    console_logs: List[str],
    url_query: str,
) -> None:
    """Raise :class:`CredentialLeakError` if ``password`` appears in storage/logs/URL."""
    for name, container in (("localStorage", local_storage), ("sessionStorage", session_storage)):
        for key, value in container.items():
            if password and password in str(value):
                raise CredentialLeakError(f"password found in {name}[{key}]")
    for line in console_logs:
        if password and password in line:
            raise CredentialLeakError("password found in console log")
    if password and password in url_query:
        raise CredentialLeakError("password found in URL query")


def assert_token_not_in_url(token: Optional[str], url: str) -> None:
    """Raise :class:`CredentialLeakError` if ``token`` appears in ``url``."""
    if token and token in url:
        raise CredentialLeakError("token found in URL")
