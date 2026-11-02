"""Client-side form validation rules.

Account format, required checks and field-level error mapping are centralized so
the final credential type (email / phone / username) can be swapped in one place
(AC-DEM-1015-004).

The default credential type is email-like: exactly one ``@``, a non-empty local
part, and a dotted domain whose labels are all non-empty. Empty domain labels
(``a@.com``, ``a@b..com``, ``a@b.``) are rejected because browsers/MTAs treat
them as malformed and a lenient check would let typos through to the backend.
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

_MIN_TLD_LENGTH = 2


def validate_account(value: str) -> Optional[str]:
    """Return an error key if the account is invalid, otherwise ``None``.

    Validation runs on the trimmed value so leading/trailing spaces never change
    the outcome, and the same trimmed value is what gets submitted.
    """
    value = value.strip()
    if not value:
        return ACCOUNT_REQUIRED
    if value.count("@") != 1:
        return ACCOUNT_INVALID_FORMAT
    local, _, domain = value.partition("@")
    if not local or not domain:
        return ACCOUNT_INVALID_FORMAT
    if any(ch not in _ACCOUNT_ALLOWED for ch in value):
        return ACCOUNT_INVALID_FORMAT
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return ACCOUNT_INVALID_FORMAT
    labels = domain.split(".")
    if len(labels) < 2:
        return ACCOUNT_INVALID_FORMAT
    if any(not label for label in labels):
        return ACCOUNT_INVALID_FORMAT
    if len(labels[-1]) < _MIN_TLD_LENGTH:
        return ACCOUNT_INVALID_FORMAT
    return None


def validate_password(value: str) -> Optional[str]:
    """Return an error key if the password is empty, otherwise ``None``.

    Passwords are never trimmed: leading/trailing spaces are significant and
    silently altering them would cause hard-to-diagnose login failures.
    """
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
