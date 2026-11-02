"""Security helpers: safe redirect, token storage policy, credential-leak checks.

Implements the OWASP ASVS L1 login-related baseline: no credential/token in URL,
no token in client storage when an HttpOnly cookie is used, and open-redirect
protection on the post-login ``redirect`` parameter (AC-DEM-1015-008 / 014).

Redirect validation is deliberately strict: browsers normalise backslashes and
strip tabs/newlines when resolving ``new URL(value, origin)``, so ``/\\evil.example``
becomes ``https://evil.example/`` in every mainstream engine even though it starts
with ``/``. Such payloads are rejected here rather than at the URL parser.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

DEFAULT_REDIRECT = "/"

# Characters browsers ignore/normalise inside URLs, used to smuggle a host.
_FORBIDDEN_REDIRECT_CHARS = ("\\", "\t", "\n", "\r", "\x00", "\f", "\v")

_REQUIRED_COOKIE_ATTRS = ("httponly", "secure", "samesite")


def normalize_redirect(redirect: Optional[str]) -> str:
    """Strip surrounding whitespace from a redirect target (``""`` when absent)."""
    if not redirect:
        return ""
    return redirect.strip()


def is_safe_redirect(redirect: Optional[str]) -> bool:
    """Return True only for same-site relative paths (no scheme / netloc / ``//``).

    Rejects absolute URLs, protocol-relative targets (``//evil``), backslash and
    control-character smuggling (``/\\evil``, ``/<TAB>/evil``), which browsers
    would otherwise resolve to an external origin.
    """
    target = normalize_redirect(redirect)
    if not target:
        return False
    if not target.startswith("/"):
        return False
    if target.startswith("//"):
        return False
    if any(ch in target for ch in _FORBIDDEN_REDIRECT_CHARS):
        return False
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return False
    return True


def resolve_redirect(redirect: Optional[str], default: str = DEFAULT_REDIRECT) -> str:
    """Resolve a post-login redirect, falling back to ``default`` when unsafe/missing.

    The returned value is normalised (whitespace stripped) so callers never
    navigate with a padded target.
    """
    target = normalize_redirect(redirect)
    if is_safe_redirect(target):
        return target
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


def is_hardened_cookie(set_cookie: Optional[str]) -> bool:
    """Return True when a ``Set-Cookie`` value carries HttpOnly/Secure/SameSite."""
    if not set_cookie:
        return False
    lowered = set_cookie.lower()
    return all(attr in lowered for attr in _REQUIRED_COOKIE_ATTRS)


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
