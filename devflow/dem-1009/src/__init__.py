"""商品搜索模块（demand:19 / DEM-1009）。

提供只读的 GET /products/search 接口能力，实现不依赖任何第三方库
（仅使用 Python 标准库），pytest 作为测试栈（开发期依赖）。

分层：
- errors:  错误码常量与错误响应 envelope
- schemas: 领域模型与序列化白名单（price 两位小数）
- store:   商品数据访问（内存实现，可替换为 ORM/数据库实现）
- service: 搜索业务逻辑（参数校验、limit 钳制、通配符转义、排序、total）
- api:     HTTP 路由层封装（返回 (status_code, body)）
"""

from .api import search_products_endpoint
from .errors import (
    INVALID_KEYWORD,
    INVALID_LIMIT,
    SearchValidationError,
    error_envelope,
)
from .schemas import Product, ProductSearchItem, ProductSearchResponse, round_price
from .service import (
    DEFAULT_LIMIT,
    MAX_KEYWORD_LENGTH,
    MAX_LIMIT,
    MIN_LIMIT,
    build_like_pattern,
    escape_like,
    parse_limit,
    search_products,
    validate_keyword,
)
from .store import ProductStore

__all__ = [
    "search_products_endpoint",
    "search_products",
    "validate_keyword",
    "parse_limit",
    "escape_like",
    "build_like_pattern",
    "DEFAULT_LIMIT",
    "MIN_LIMIT",
    "MAX_LIMIT",
    "MAX_KEYWORD_LENGTH",
    "INVALID_KEYWORD",
    "INVALID_LIMIT",
    "SearchValidationError",
    "error_envelope",
    "Product",
    "ProductSearchItem",
    "ProductSearchResponse",
    "round_price",
    "ProductStore",
]
