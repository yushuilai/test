"""搜索业务逻辑：参数校验、limit 钳制、通配符转义、排序与 total。

对外主入口为 :func:`search_products`。校验顺序保证「先校验参数、再访问数据」，
即非法请求不会触达 store（AC-002 的「不执行任何数据库查询」）。

约定：
- keyword：必填，strip 后非空，长度 <= 100；否则 400 INVALID_KEYWORD。
- limit：缺失 -> 默认 20；<1 -> 钳到 1；>100 -> 钳到 100；非整数 -> 400 INVALID_LIMIT。
- total：全量命中数（不受 limit 影响）。
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from .errors import INVALID_KEYWORD, INVALID_LIMIT, SearchValidationError
from .schemas import Product, ProductSearchItem, ProductSearchResponse, round_price
from .store import ProductStore

DEFAULT_LIMIT = 20
MIN_LIMIT = 1
MAX_LIMIT = 100
MAX_KEYWORD_LENGTH = 100

# LIKE 的转义符约定：固定使用反斜杠（SQL: ESCAPE '\\'）
LIKE_ESCAPE_CHAR = "\\"


def validate_keyword(keyword: object) -> str:
    """校验并规整 keyword，返回 strip 后的关键词；非法时抛 400 异常。"""
    if keyword is None or not isinstance(keyword, str):
        raise SearchValidationError(INVALID_KEYWORD, "keyword is required")
    stripped = keyword.strip()
    if not stripped:
        raise SearchValidationError(INVALID_KEYWORD, "keyword must not be empty")
    if len(stripped) > MAX_KEYWORD_LENGTH:
        raise SearchValidationError(
            INVALID_KEYWORD, f"keyword must not exceed {MAX_KEYWORD_LENGTH} characters"
        )
    return stripped


def clamp_limit(value: int) -> int:
    """将 limit 钳制到 [1, 100]。"""
    return max(MIN_LIMIT, min(MAX_LIMIT, value))


def parse_limit(limit: object) -> int:
    """解析并钳制 limit；缺失返回默认值，非整数抛 400。"""
    if limit is None:
        return DEFAULT_LIMIT
    if isinstance(limit, bool):
        # bool 是 int 子类，先排除，避免 True/False 被当整数
        raise SearchValidationError(INVALID_LIMIT, "limit must be an integer")
    if isinstance(limit, int):
        value = limit
    elif isinstance(limit, str):
        raw = limit.strip()
        if raw == "":
            raise SearchValidationError(INVALID_LIMIT, "limit must be an integer")
        try:
            value = int(raw)
        except ValueError as exc:
            raise SearchValidationError(
                INVALID_LIMIT, "limit must be an integer"
            ) from exc
    else:
        raise SearchValidationError(INVALID_LIMIT, "limit must be an integer")
    return clamp_limit(value)


def escape_like(keyword: str) -> str:
    """转义 LIKE 模式中的特殊字符，转义顺序：``\\`` -> ``%`` -> ``_``。

    反斜杠必须最先转义，否则后转义的 ``%``/``_`` 会被误转。
    """
    return (
        keyword.replace(LIKE_ESCAPE_CHAR, LIKE_ESCAPE_CHAR * 2)
        .replace("%", LIKE_ESCAPE_CHAR + "%")
        .replace("_", LIKE_ESCAPE_CHAR + "_")
    )


def build_like_pattern(keyword: str) -> str:
    """构造含前后通配的 LIKE 模式（``%escaped%``），供 SQL 侧使用。"""
    return "%" + escape_like(keyword) + "%"


def _to_items(products: List[Product]) -> List[ProductSearchItem]:
    return [
        ProductSearchItem(
            id=p.id, name=p.name, price=round_price(p.price), stock=p.stock
        )
        for p in products
    ]


def search_products(
    store: ProductStore, keyword: object, limit: object = None
) -> ProductSearchResponse:
    """执行搜索：先校验 keyword 与 limit，再访问 store。"""
    validated_keyword = validate_keyword(keyword)
    effective_limit = parse_limit(limit)

    matched, total = store.search(validated_keyword, effective_limit)
    return ProductSearchResponse(items=_to_items(matched), total=total)
