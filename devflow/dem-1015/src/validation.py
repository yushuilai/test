"""Client-side form validation rules.

Account format, required checks and field-level error mapping are centralized so
the final credential type (email / phone / username) can be swapped in one place
(AC-DEM-1015-004).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

ACCOUNT_REQUIRED = "account_required"
PASSWORD_REQUIRED = "password_required"
ACCOUNT_INVALID_FORMAT = "account_invalid_format"

_ACCOUNT_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._%+-@"
)


def validate_account(value: str) -> Optional[str]:
    """Return an error key if the account is invalid, otherwise ``None``.

    The default credential type is an email-like account: a single ``@`` with a
    non-empty local part and a dotted, non-empty domain, using only allow-listed
    characters.
    """
    value = value.strip()
    if not value:
        return ACCOUNT_REQUIRED
    if value.count("@") != 1:
        return ACCOUNT_INVALID_FORMAT
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain:
        return ACCOUNT_INVALID_FORMAT
    if any(ch not in _ACCOUNT_ALLOWED for ch in value):
        return ACCOUNT_INVALID_FORMAT
    return None


def validate_password(value: str) -> Optional[str]:
    """Return an error key if the password is empty, otherwise ``None``."""
    if not value:
        return PASSWORD_REQUIRED
    return None


@dataclass
class ValidationResult:
    """Field-level validation outcome for the form."""

    account_error: Optional[str] = None
    password_error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Return True when neither field has an error."""
        return self.account_error is None and self.password_error is None


def validate_form(account: str, password: str) -> ValidationResult:
    """Validate both fields and return a combined result."""
    return ValidationResult(
        account_error=validate_account(account),
        password_error=validate_password(password),
    )
