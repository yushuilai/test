"""Semantic page shell: focusable elements, keyboard order and rendered HTML.

The focusable controls are modelled as data so accessible names, keyboard order
and Enter-to-submit can be asserted in Python, and ``render_page_html`` emits a
complete, self-contained static page (inline CSS + a small mock-auth script) that
opens in a browser with zero backend.

Spec reconciliation (AC-002 vs AC-005): AC-002 enumerates five required controls
(account, password, submit, remember, forgot) while AC-005 mandates a password
visibility toggle, which is itself a focusable button. The tab sequence therefore
holds six stops — the five AC-002 controls plus the in-field toggle — and
``REQUIRED_CONTROLS`` keeps the AC-002 set explicit for verification. Dropping the
toggle from the tab order would make it keyboard-unreachable, which is worse than
a one-stop deviation from the literal count.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from string import Template
from typing import Iterable, List, Optional

from .design_tokens import DEFAULT_TOKENS
from .i18n import get_message, message_catalog
from .motion import EASE_OUT_EASING

TITLE = "登录"


@dataclass(frozen=True)
class FocusableElement:
    """A focusable, screen-reader-accessible control in visual reading order."""

    id: str
    kind: str  # "input" | "button" | "checkbox" | "link"
    label: str  # accessible name (visible <label> / aria-label)
    aria_label: str


# AC-002 enumerates exactly these five controls.
REQUIRED_CONTROLS: List[FocusableElement] = [
    FocusableElement("account", "input", "账号", "账号"),
    FocusableElement("password", "input", "密码", "密码"),
    FocusableElement("remember", "checkbox", "记住我", "记住我"),
    FocusableElement("forgot", "link", "忘记密码", "忘记密码"),
    FocusableElement("submit", "button", "登录", "登录"),
]

# Full tab sequence: DOM order == visual reading order == keyboard order (AC-009).
FOCUSABLE_ELEMENTS: List[FocusableElement] = [
    FocusableElement("account", "input", "账号", "账号"),
    FocusableElement("password", "input", "密码", "密码"),
    FocusableElement("password-toggle", "button", "显示密码", "显示密码"),
    FocusableElement("remember", "checkbox", "记住我", "记住我"),
    FocusableElement("forgot", "link", "忘记密码", "忘记密码"),
    FocusableElement("submit", "button", "登录", "登录"),
]


def focus_order() -> List[str]:
    """Return the id list in focus (visual reading) order."""
    return [element.id for element in FOCUSABLE_ELEMENTS]


def required_control_ids() -> List[str]:
    """Return the ids of the five controls required by AC-DEM-1015-002."""
    return [element.id for element in REQUIRED_CONTROLS]


def all_elements_have_accessible_name(
    elements: Optional[Iterable[FocusableElement]] = None,
) -> bool:
    """Return True when every focusable element has a label or aria-label."""
    scope = list(elements) if elements is not None else FOCUSABLE_ELEMENTS
    return all(element.label or element.aria_label for element in scope)


def next_tab_focus(current_index: int) -> Optional[int]:
    """Return the next tab stop index, or None when focus leaves the page.

    Returning None at the end means the focus is not trapped inside the page.
    """
    if current_index < 0 or current_index >= len(FOCUSABLE_ELEMENTS):
        raise IndexError("tab index out of range")
    if current_index + 1 < len(FOCUSABLE_ELEMENTS):
        return current_index + 1
    return None


def _render_params() -> dict:
    """Collect every token/message the template needs (single source of truth)."""
    tokens = DEFAULT_TOKENS
    return {
        "title": TITLE,
        "bg": tokens.background,
        "surface": tokens.surface,
        "primary": tokens.primary,
        "secondary": tokens.secondary,
        "text": tokens.text_primary,
        "text_dim": tokens.text_secondary,
        "error": tokens.error,
        "focus": tokens.focus_ring,
        "radius": f"{tokens.radius_px}px",
        "glow": f"{tokens.glow_blur_px}px",
        "dur": f"{tokens.motion_duration_ms}ms",
        "ease": EASE_OUT_EASING,
        "font_stack": tokens.font_stack,
        "spacing_vars": ";".join(
            f"--space-{index}:{value}px"
            for index, value in enumerate(tokens.spacing_px, start=1)
        ),
        "messages_json": json.dumps(message_catalog(), ensure_ascii=False),
        "account_label": get_message("account_label"),
        "password_label": get_message("password_label"),
        "remember_label": get_message("remember_label"),
        "forgot_label": get_message("forgot_label"),
        "submit_label": get_message("submit_label"),
        "show_password": get_message("show_password"),
        "toggle_show": get_message("toggle_show"),
        "eyebrow": get_message("eyebrow"),
        "subtitle": get_message("subtitle"),
    }


_CSS = """
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{font-family:$font_stack;background:var(--bg);color:var(--text);display:flex;align-items:center;justify-content:center;min-height:100vh;padding:var(--space-4);overflow-x:hidden;-webkit-font-smoothing:antialiased}
@font-face{font-family:'TechSans';src:local('Segoe UI'),local('PingFang SC');font-display:swap}
:root{--bg:$bg;--surface:$surface;--primary:$primary;--secondary:$secondary;--text:$text;--text-dim:$text_dim;--error:$error;--focus:$focus;--radius:$radius;--glow:$glow;--dur:$dur;--ease:$ease;$spacing_vars;}
#tech-background{position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(circle at 18% 22%,rgba(0,229,255,.16),transparent 44%),radial-gradient(circle at 82% 78%,rgba(124,77,255,.18),transparent 48%),var(--bg)}
#tech-background::before{content:'';position:absolute;inset:-48px;background-image:linear-gradient(rgba(0,229,255,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,255,.07) 1px,transparent 1px);background-size:48px 48px;animation:grid-drift 24s linear infinite}
@keyframes grid-drift{from{transform:translate3d(0,0,0)}to{transform:translate3d(48px,48px,0)}}
#login-card{position:relative;z-index:1;width:min(420px,100%);padding:var(--space-6);border-radius:var(--radius);background:linear-gradient(160deg,rgba(18,24,43,.94),rgba(10,14,26,.9));border:1px solid rgba(0,229,255,.28);box-shadow:0 0 calc(var(--glow) * 1.5) rgba(0,229,255,.16),inset 0 1px 0 rgba(255,255,255,.06);backdrop-filter:blur(12px);animation:card-in 320ms var(--ease) both}
@keyframes card-in{from{opacity:0;transform:translate3d(0,12px,0)}to{opacity:1;transform:none}}
.eyebrow{margin:0 0 var(--space-2);font-size:11px;letter-spacing:.32em;color:var(--primary);text-transform:uppercase}
h1{margin:0 0 var(--space-2);font-size:28px;letter-spacing:.08em;color:var(--text)}
.subtitle{margin:0 0 var(--space-6);font-size:13px;line-height:1.6;color:var(--text-dim)}
.field{margin:0 0 var(--space-4)}
label{display:block;margin:0 0 var(--space-1);font-size:13px;color:var(--text-dim)}
input[type='text'],input[type='password']{width:100%;min-height:48px;padding:0 var(--space-3);border-radius:10px;border:1px solid rgba(138,151,181,.35);background:rgba(10,14,26,.72);color:var(--text);font-size:15px;transition:border-color var(--dur) var(--ease),box-shadow var(--dur) var(--ease)}
input[type='text']:hover,input[type='password']:hover{border-color:rgba(0,229,255,.45)}
input:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-color:var(--focus);box-shadow:0 0 0 4px rgba(0,229,255,.14)}
input[aria-invalid='true']{border-color:var(--error)}
.input-row{position:relative;display:flex;align-items:center}
.input-row input{padding-right:76px}
#password-toggle{position:absolute;right:var(--space-1);min-height:44px;min-width:56px;padding:0 var(--space-2);border:1px solid rgba(0,229,255,.32);border-radius:8px;background:rgba(0,229,255,.08);color:var(--primary);font-size:12px;letter-spacing:.08em;cursor:pointer;transition:background var(--dur) var(--ease),box-shadow var(--dur) var(--ease)}
#password-toggle:hover{background:rgba(0,229,255,.16);box-shadow:0 0 var(--glow) rgba(0,229,255,.28)}
#password-toggle:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
#password-toggle[aria-pressed='true']{background:rgba(124,77,255,.22);border-color:rgba(124,77,255,.5);color:var(--text)}
.row{display:flex;align-items:center;gap:var(--space-2);margin:0 0 var(--space-4);font-size:13px}
.row label{display:flex;align-items:center;min-height:44px;margin:0;color:var(--text-dim);cursor:pointer}
#remember{width:18px;height:18px;accent-color:var(--primary)}
#forgot{margin-left:auto;color:var(--primary);text-decoration:none;border-bottom:1px solid transparent;transition:border-color var(--dur) var(--ease)}
#forgot:hover{border-bottom-color:var(--primary)}
#forgot:focus-visible{outline:2px solid var(--focus);outline-offset:3px}
.field-error{min-height:18px;margin:var(--space-1) 0 0;font-size:12px;line-height:1.5;color:var(--error)}
.form-error{margin:0 0 var(--space-3);font-size:13px;line-height:1.5;color:var(--error)}
#submit{width:100%;min-height:48px;border:0;border-radius:10px;background:linear-gradient(120deg,var(--primary),var(--secondary));color:#04121A;font-size:15px;font-weight:600;letter-spacing:.12em;cursor:pointer;box-shadow:0 0 var(--glow) rgba(0,229,255,.32);transition:transform var(--dur) var(--ease),box-shadow var(--dur) var(--ease),filter var(--dur) var(--ease)}
#submit:hover{filter:brightness(1.08);box-shadow:0 0 calc(var(--glow) * 1.6) rgba(0,229,255,.5)}
#submit:active{transform:translateY(1px)}
#submit:focus-visible{outline:2px solid var(--text);outline-offset:2px}
#submit:disabled{opacity:.6;cursor:not-allowed;filter:none;box-shadow:none}
.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
@media (max-width:480px){body{padding:var(--space-3)}#login-card{padding:var(--space-5)}}
@media (min-width:1440px){#login-card{width:420px}}
@media (prefers-reduced-motion: reduce){#tech-background::before{animation:none}#login-card{animation:none}*{transition-duration:100ms!important}}
"""

_JS = """
(function () {
  'use strict';
  var MSG = $messages_json;
  var form = document.getElementById('login-form');
  var accountInput = document.getElementById('account');
  var passwordInput = document.getElementById('password');
  var accountError = document.getElementById('account-error');
  var passwordError = document.getElementById('password-error');
  var formError = document.getElementById('form-error');
  var status = document.getElementById('submit-status');
  var toggle = document.getElementById('password-toggle');
  var toggleText = document.getElementById('password-toggle-text');
  var submit = document.getElementById('submit');
  var loading = false;
  var ACCOUNT_RE = /^[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\\.)+[A-Za-z]{2,}$/;

  function setFieldError(input, node, message) {
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
    node.textContent = message;
  }

  function validateAccount(value) {
    if (!value) { return MSG.account_required; }
    if (!ACCOUNT_RE.test(value)) { return MSG.account_invalid_format; }
    return '';
  }

  function validatePassword(value) {
    if (!value) { return MSG.password_required; }
    return '';
  }

  function safeRedirect(target) {
    if (typeof target !== 'string') { return '/'; }
    var value = target.trim();
    if (value.charAt(0) !== '/' || value.charAt(1) === '/' || value.indexOf('\\\\') > -1) { return '/'; }
    return value;
  }

  function mockLogin(credentials) {
    return new Promise(function (resolve) {
      window.setTimeout(function () {
        var ok = credentials.account === 'user@example.com' && credentials.password === 'secret123';
        resolve({ ok: ok, redirect: ok ? '/dashboard' : null });
      }, 600);
    });
  }

  toggle.addEventListener('click', function () {
    var reveal = passwordInput.type === 'password';
    passwordInput.type = reveal ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', reveal ? 'true' : 'false');
    toggle.setAttribute('aria-label', reveal ? MSG.hide_password : MSG.show_password);
    toggleText.textContent = reveal ? MSG.toggle_hide : MSG.toggle_show;
    passwordInput.focus();
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (loading) { return; }
    var account = accountInput.value.trim();
    var accountMessage = validateAccount(account);
    var passwordMessage = validatePassword(passwordInput.value);
    setFieldError(accountInput, accountError, accountMessage);
    setFieldError(passwordInput, passwordError, passwordMessage);
    formError.textContent = '';
    if (accountMessage || passwordMessage) { return; }
    loading = true;
    submit.disabled = true;
    submit.setAttribute('aria-busy', 'true');
    status.textContent = MSG.submitting;
    mockLogin({ account: account, password: passwordInput.value }).then(function (result) {
      loading = false;
      submit.disabled = false;
      submit.removeAttribute('aria-busy');
      status.textContent = result.ok ? MSG.login_success : MSG.invalid_credentials;
      if (result.ok) {
        window.location.assign(safeRedirect(result.redirect));
        return;
      }
      formError.textContent = MSG.invalid_credentials;
    });
  });
}());
"""

_PAGE_TEMPLATE = Template(
    """<!doctype html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>
<meta name='color-scheme' content='dark'>
<meta name='description' content='科技感登录页'>
<title>$title</title>
<style>$css
</style>
</head>
<body>
<div id='tech-background' aria-hidden='true'></div>
<main id='login-card'>
<p class='eyebrow' aria-hidden='true'>$eyebrow</p>
<h1>$title</h1>
<p class='subtitle'>$subtitle</p>
<form id='login-form' novalidate>
<div class='field'>
<label for='account'>$account_label</label>
<input id='account' name='account' type='text' inputmode='email' autocomplete='username' aria-describedby='account-error' aria-invalid='false' placeholder='user@example.com'>
<p id='account-error' class='field-error'></p>
</div>
<div class='field'>
<label for='password'>$password_label</label>
<div class='input-row'>
<input id='password' name='password' type='password' autocomplete='current-password' aria-describedby='password-error' aria-invalid='false'>
<button id='password-toggle' type='button' aria-pressed='false' aria-label='$show_password'><span id='password-toggle-text' aria-hidden='true'>$toggle_show</span></button>
</div>
<p id='password-error' class='field-error'></p>
</div>
<div class='row'>
<input id='remember' name='remember' type='checkbox'>
<label for='remember'>$remember_label</label>
<a id='forgot' href='/forgot'>$forgot_label</a>
</div>
<p id='form-error' class='form-error' role='alert' aria-live='assertive' aria-atomic='true'></p>
<button id='submit' type='submit'>$submit_label</button>
<p id='submit-status' class='sr-only' aria-live='polite'></p>
</form>
</main>
<script>$js
</script>
</body>
</html>
"""
)


def render_page_html() -> str:
    """Render the static login page HTML with all six focusable controls."""
    params = _render_params()
    params["css"] = Template(_CSS).safe_substitute(params)
    params["js"] = Template(_JS).safe_substitute(params)
    return _PAGE_TEMPLATE.safe_substitute(params)


def html_has_core_content(html: str) -> bool:
    """Return True when title, account, password and login button are present."""
    checks = (
        f"<title>{TITLE}</title>",
        "id='account'",
        "id='password'",
        "id='submit'",
    )
    return all(check in html for check in checks)


def html_has_aria_state_containers(html: str) -> bool:
    """Return True when error/live regions and ARIA bindings are present."""
    checks = (
        "aria-describedby",
        "id='account-error'",
        "id='password-error'",
        "role='alert'",
        "aria-live",
        "aria-invalid",
    )
    return all(check in html for check in checks)
