"""业务逻辑：入参校验、limit 钳制、price 舍入与结果组装。

对外统一通过 ``search(keyword, limit)`` 返回 ``SearchResult``，
非法入参抛出 ``ValidationError``（由 HTTP 层映射为 400 与固定错误体）。

关键口径（对应 req_spec 验收标准）：
- keyword: 缺失/空串/纯空白/超长(>128) -> 400 INVALID_KEYWORD
- limit:   缺失 -> 默认 20；<=0 -> 钳制到 1；>100 -> 钳制到 100；
           非整数 -> 400 INVALID_LIMIT
- 校验在触达数据层之前完成（空 keyword 不会调用 repository，可 mock 断言）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Union

from product_search.models import (
    ProductSearchItem,
    ProductSearchResponse,
    format_price,
)
from product_search.repository import ProductRepository

# 限制值口径
DEFAULT_LIMIT = 20
MIN_LIMIT = 1
MAX_LIMIT = 100
MAX_KEYWORD_LENGTH = 128

# 匹配整数（可带正负号）的完整串，用于判定 limit 是否为整数
_INT_RE = re.compile(r"^[+-]?\d+$")


class ValidationError(Exception):
    """入参校验失败，映射为 HTTP 400 与固定错误体。

    ``code`` 为稳定错误码（INVALID_KEYWORD / INVALID_LIMIT），
    ``message`` 为非空人类可读说明。
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


@dataclass(frozen=True)
class SearchResult:
    """服务层成功结果。"""

    response: ProductSearchResponse


class ProductSearchService:
    """商品搜索服务。"""

    def __init__(self, repository: ProductRepository | None = None) -> None:
        self._repository = repository or ProductRepository()

    @property
    def repository(self) -> ProductRepository:
        """暴露仓储以便测试注入 mock 断言「空 keyword 不触达数据层」。"""
        return self._repository

    # ------------------------------------------------------------------ #
    # 公开入口
    # ------------------------------------------------------------------ #
    def search(self, keyword: Optional[str], limit: Optional[Union[str, int]] = None) -> SearchResult:
        """执行搜索。

        :param keyword: 原始 keyword（来自查询串，可为 None 表示缺失）
        :param limit: 原始 limit（字符串或整数，可为 None 表示缺失）
        :return: 成功结果；非法入参抛 ValidationError
        """
        kw = self._normalize_keyword(keyword)
        lim = self._normalize_limit(limit)
        rows, total = self._repository.search_by_name(kw, lim)
        items: List[ProductSearchItem] = [
            ProductSearchItem(
                id=p.id,
                name=p.name,
                price=format_price(p.price),
                stock=p.stock,
            )
            for p in rows
        ]
        return SearchResult(response=ProductSearchResponse(items=items, total=total))

    # ------------------------------------------------------------------ #
    # 归一化
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_keyword(keyword: Optional[str]) -> str:
        if keyword is None:
            raise ValidationError("INVALID_KEYWORD", "keyword 参数缺失")
        if not isinstance(keyword, str):
            raise ValidationError("INVALID_KEYWORD", "keyword 必须是字符串")
        kw = keyword.strip()
        if not kw:
            raise ValidationError("INVALID_KEYWORD", "keyword 不能为空")
        if len(kw) > MAX_KEYWORD_LENGTH:
            raise ValidationError(
                "INVALID_KEYWORD", f"keyword 长度不能超过 {MAX_KEYWORD_LENGTH}"
            )
        return kw

    @staticmethod
    def _normalize_limit(limit: Optional[Union[str, int]]) -> int:
        if limit is None:
            return DEFAULT_LIMIT
        if isinstance(limit, bool):
            # bool 是 int 子类，显式拒绝，避免 True/False 被当作 1/0
            raise ValidationError("INVALID_LIMIT", "limit 必须是整数")
        if isinstance(limit, int):
            value = limit
        elif isinstance(limit, str):
            stripped = limit.strip()
            if not _INT_RE.fullmatch(stripped):
                raise ValidationError("INVALID_LIMIT", "limit 必须是整数")
            value = int(stripped)
        else:
            raise ValidationError("INVALID_LIMIT", "limit 必须是整数")
        if value <= 0:
            return MIN_LIMIT
        if value > MAX_LIMIT:
            return MAX_LIMIT
        return value
