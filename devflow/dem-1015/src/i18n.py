"""Localized message resources (zh-CN only for this release).

The unified failure copy required by AC-DEM-1015-007 lives here so it cannot be
accidentally rewritten into an account-enumerating message. The structure is
i18n-ready: adding a locale means adding one dict, no component changes.
"""

from __future__ import annotations

MESSAGES = {
    "account_required": "请输入账号",
    "password_required": "请输入密码",
    "account_invalid_format": "账号格式不正确，请检查是否包含 @ 及合法字符",
    "invalid_credentials": "账号或密码错误",
    "rate_limited": "请求过于频繁，请稍后再试",
    "account_locked": "账号暂时锁定，请稍后再试",
    "server_error": "服务暂时不可用，请稍后再试",
    "network_error": "网络异常，请检查网络连接",
    "login_success": "登录成功",
    "submitting": "正在登录…",
}


def get_message(key: str) -> str:
    """Return the localized message for ``key`` (falls back to the key itself)."""
    return MESSAGES.get(key, key)
