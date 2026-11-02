"""独立验收测试（测试角色补写，不复用开发自测断言）。

目的：绕过开发方「自证式」用例，从真实契约与浏览器语义出发复验 AC，
并把开发自测未覆盖的分支（423/429/超时、重定向绕过、渲染层 aria 状态）
暴露为可执行断言。

约定：以 ``test_ind_`` 开头的用例为独立用例；失败即代表实现存在缺陷，
不得改断言迁就实现。
"""

from __future__ import annotations

import pytest

from src.auth import MockAuthAdapter
from src.i18n import get_message
from src.login_form import LoginForm
from src.page_shell import render_page_html
from src.security import is_safe_redirect, resolve_redirect
from src.validation import ACCOUNT_INVALID_FORMAT, validate_account

VALID_ACCOUNT = "user@example.com"
VALID_PASSWORD = "secret123"


# TC-IND-01 / AC-008：开放重定向绕过（反斜杠在浏览器中被归一为 "/"）
@pytest.mark.parametrize(
    "payload",
    [
        "/\\evil.example",  # WHATWG: new URL('/\\evil.example','https://good') -> https://evil.example/
        "/\\/evil.example",
        "/\t/evil.example",
        "/\n/evil.example",
    ],
)
def test_ind_01_redirect_backslash_and_control_chars_rejected(payload: str) -> None:
    assert is_safe_redirect(payload) is False, f"开放重定向未拦截: {payload!r}"
    assert resolve_redirect(payload) == "/"


# TC-IND-02 / AC-008：合法站内路径仍需放行（防止修复过严）
@pytest.mark.parametrize("payload", ["/dashboard", "/a/b?x=1#h", "/"])
def test_ind_02_legit_relative_redirect_allowed(payload: str) -> None:
    assert resolve_redirect(payload) == payload


# TC-IND-03 / AC-007：423/429 分支可被触达且不泄露原始错误
@pytest.mark.parametrize("status", [423, 429, 500])
def test_ind_03_error_codes_reachable_with_valid_credentials(status: int) -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter(status_code=status))
    result = form.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert result is not None and result.success is False
    assert form.form_error_message, f"status={status} 无用户可见文案"
    assert "connection pool" not in form.form_error_message
    assert form.form_error_alert_role == "alert"


# TC-IND-04 / AC-007 + NFR 安全：任何失败文案都不得区分「账号不存在」与「密码错误」
@pytest.mark.parametrize("status", [401, 423])
def test_ind_04_failure_copy_not_enumerating(status: int) -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter(status_code=status))
    form.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form.form_error_message == get_message("invalid_credentials")


# TC-IND-05 / AC-006：超时/断网也可被 mock 注入且映射为网络提示
@pytest.mark.parametrize("mode", ["timeout", "network"])
def test_ind_05_timeout_and_network_mapped(mode: str) -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter(raise_error=mode))
    form.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form.form_error_message == get_message("network_error")


# TC-IND-06 / AC-003：二次提交时旧的整体错误应清除，避免新旧错误并存
def test_ind_06_stale_form_error_cleared_on_next_validation_failure() -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter(status_code=401))
    form.submit(VALID_ACCOUNT, "wrong-password")
    assert form.form_error_message == get_message("invalid_credentials")
    form.submit("", "")
    assert form.form_error_message == "", "整体错误未清除，与新字段错误并存"


# TC-IND-07 / AC-004：账号提交值应与校验值一致（去除首尾空白）
def test_ind_07_trimmed_account_submitted_to_adapter() -> None:
    adapter = MockAuthAdapter()
    form = LoginForm(auth_adapter=adapter)
    form.submit("  user@example.com  ", VALID_PASSWORD)
    assert adapter.calls, "校验通过却未发起请求"
    assert adapter.calls[0].account == VALID_ACCOUNT


# TC-IND-08 / AC-004：域名空标签应判为格式错误
@pytest.mark.parametrize("account", ["a@.com", "a@b..com", "a@b."])
def test_ind_08_domain_empty_label_rejected(account: str) -> None:
    assert validate_account(account) == ACCOUNT_INVALID_FORMAT


# TC-IND-09 / AC-003 + AC-007：渲染页面必须含错误容器、aria-describedby 与 role=alert
def test_ind_09_rendered_dom_has_error_containers() -> None:
    html = render_page_html()
    assert "aria-describedby" in html, "输入框未与错误文案建立 aria 关联"
    assert "id='account-error'" in html and "id='password-error'" in html
    assert "role='alert'" in html, "整体错误区域缺少 role=alert，读屏无法播报"
    assert "aria-invalid" in html
    assert "aria-live" in html, "提交中状态缺少 live region"


# TC-IND-10 / AC-005：渲染页面必须含密码显隐按钮且带 aria-pressed
def test_ind_10_rendered_dom_has_password_toggle() -> None:
    html = render_page_html()
    assert "aria-pressed" in html, "密码显隐按钮缺失或未同步 aria-pressed"
    assert "type='button'" in html, "显隐控件不应为 submit 类型"


# TC-IND-11 / AC-002：显隐按钮也属可聚焦控件，数量与 AC-002 的「5 个」需一致
def test_ind_11_focusable_count_matches_contract() -> None:
    from src.page_shell import FOCUSABLE_ELEMENTS

    ids = [e.id for e in FOCUSABLE_ELEMENTS]
    assert "password-toggle" in ids, "可聚焦元素清单缺少密码显隐按钮（与 AC-005 冲突）"


# TC-IND-12 / AC-013：装饰层不得进入 Tab 序列且应 aria-hidden
def test_ind_12_decorative_layer_isolated() -> None:
    html = render_page_html()
    assert "aria-hidden='true'" in html
    assert "tabindex='0'" not in html


# TC-IND-13 / AC-008：一次成功后再失败，旧的跳转目标必须清空，避免失败后仍导航
def test_ind_13_pending_redirect_cleared_on_subsequent_failure() -> None:
    form = LoginForm(auth_adapter=MockAuthAdapter())
    form.submit(VALID_ACCOUNT, VALID_PASSWORD)
    assert form.pending_redirect == "/dashboard"
    form.submit(VALID_ACCOUNT, "wrong-password")
    assert form.form_error_message == get_message("invalid_credentials")
    assert form.pending_redirect is None, "登录失败后仍残留上一次的跳转目标"


# TC-IND-14 / AC-008：校验时 strip 而返回时未 strip，跳转值前后不一致
def test_ind_14_redirect_padding_normalized() -> None:
    assert resolve_redirect("  /dashboard") == "/dashboard"
    assert resolve_redirect("\t/dashboard") == "/dashboard"
