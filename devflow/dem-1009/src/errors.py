"""错误码常量与错误响应 envelope。

错误响应契约（HTTP 400 时）：
    {"code": "<稳定错误码>", "message": "<人类可读信息>"}

错误码集中定义，避免散落字面量；前端可依赖 ``code`` 做程序化区分。
"""

from __future__ import annotations

from typing import Any, Dict

# 稳定错误码（对外契约，禁止随意变更）
INVALID_KEYWORD = "INVALID_KEYWORD"
INVALID_LIMIT = "INVALID_LIMIT"


class SearchValidationError(Exception):
    """搜索接口的参数校验异常，携带稳定错误码与提示信息。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def error_envelope(code: str, message: str) -> Dict[str, Any]:
    """构造统一错误响应体。"""
    return {"code": code, "message": message}
