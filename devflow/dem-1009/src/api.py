"""HTTP 路由层封装。

不依赖具体 Web 框架，直接返回 ``(status_code, body_dict)``，便于：
- 单测直接断言状态码与响应体；
- 接入 FastAPI/Flask 时只需一层薄适配（``return JSONResponse(...)``）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

from .errors import SearchValidationError, error_envelope
from .service import search_products
from .store import ProductStore


def search_products_endpoint(
    keyword: object, limit: object = None, store: Optional[ProductStore] = None
) -> Tuple[int, Dict[str, Any]]:
    """GET /products/search 的处理器。

    返回 ``(200, {items, total})`` 或 ``(400, {code, message})``。
    """
    if store is None:
        store = ProductStore([])
    try:
        response = search_products(store, keyword, limit)
        return 200, response.to_dict()
    except SearchValidationError as exc:
        return 400, error_envelope(exc.code, exc.message)
