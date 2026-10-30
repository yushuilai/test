"""Semantic page shell: focusable elements, keyboard order and rendered HTML.

The five focusable controls required by AC-DEM-1015-002 are modelled as data so
accessible names, keyboard order and Enter-to-submit can be asserted in Python.
The rendered HTML is a real static page that can be opened in a browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

TITLE = "登录"

_FONT_STACK = "'Segoe UI', system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif"


@dataclass(frozen=True)
class FocusableElement:
    """A focusable, screen-reader-accessible control in visual reading order."""

    id: str
    kind: str  # "input" | "button" | "checkbox" | "link"
    label: str  # accessible name (visible <label>)
    aria_label: str


# Visual reading order == DOM order == keyboard order (AC-DEM-1015-009).
FOCUSABLE_ELEMENTS: List[FocusableElement] = [
    FocusableElement("account", "input", "账号", "账号"),
    FocusableElement("password", "input", "密码", "密码"),
    FocusableElement("remember", "checkbox", "记住我", "记住我"),
    FocusableElement("forgot", "link", "忘记密码", "忘记密码"),
    FocusableElement("submit", "button", "登录", "登录"),
]


def focus_order() -> List[str]:
    """Return the id list in focus (visual reading) order."""
    return [element.id for element in FOCUSABLE_ELEMENTS]


def all_elements_have_accessible_name() -> bool:
    """Return True when every focusable element has a label or aria-label."""
    return all(element.label or element.aria_label for element in FOCUSABLE_ELEMENTS)


def next_tab_focus(current_index: int) -> Optional[int]:
    """Return the next tab stop index, or None when focus leaves the page.

    Returning None at the end means the focus is not trapped inside the page.
    """
    if current_index < 0 or current_index >= len(FOCUSABLE_ELEMENTS):
        raise IndexError("tab index out of range")
    if current_index + 1 < len(FOCUSABLE_ELEMENTS):
        return current_index + 1
    return None


def render_page_html() -> str:
    """Render the static login page HTML with the five focusable controls."""
    return (
        "<!doctype html>"
        "<html lang='zh-CN'>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{TITLE}</title>"
        f"<style>"
        f"@font-face{{font-family:'Segoe UI';font-display:swap;}}"
        f"body{{font-family:{_FONT_STACK};background:#0A0E1A;color:#E6F1FF;}}"
        f"#tech-background{{position:fixed;inset:0;z-index:0;}}"
        f"#login-card{{position:relative;z-index:1;max-width:420px;}}"
        f"button{{min-height:44px;}}"
        f"@media (prefers-reduced-motion: reduce){{#tech-background{{animation:none;}}}}"
        f"</style>"
        "</head>"
        "<body>"
        f"<div id='tech-background' aria-hidden='true'></div>"
        "<main id='login-card'>"
        f"<h1>{TITLE}</h1>"
        "<form id='login-form' novalidate>"
        "<label for='account'>账号</label>"
        "<input id='account' name='account' type='text' autocomplete='username'>"
        "<label for='password'>密码</label>"
        "<input id='password' name='password' type='password' autocomplete='current-password'>"
        "<input id='remember' type='checkbox'><label for='remember'>记住我</label>"
        "<a id='forgot' href='/forgot'>忘记密码</a>"
        "<button id='submit' type='submit'>登录</button>"
        "</form>"
        "</main>"
        "</body>"
        "</html>"
    )


def html_has_core_content(html: str) -> bool:
    """Return True when title, account, password and login button are present."""
    checks = (
        f"<title>{TITLE}</title>",
        "id='account'",
        "id='password'",
        "id='submit'",
    )
    return all(check in html for check in checks)
