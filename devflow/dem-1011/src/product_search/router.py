"""标准库 HTTP 层：GET /products/search 路由处理器。

仅依赖标准库（http.server / urllib.parse / json），满足「零新增运行时依赖」。
- 路由: GET /products/search
- 入参: keyword（必填）、limit（可选）
- 成功: 200 + {"items": [...], "total": N}
- 校验失败: 400 + {"error": {"code", "message"}}
- 未知路径: 404；非 GET: 405
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import parse_qs, urlparse

from product_search.service import ProductSearchService, ValidationError


class ProductSearchHandler(BaseHTTPRequestHandler):
    """GET /products/search 处理器。

    类属性 ``service`` 由创建服务时注入，便于测试复用同一数据源。
    """

    service: ProductSearchService

    # ------------------------------------------------------------------ #
    # 请求分发
    # ------------------------------------------------------------------ #
    def do_GET(self) -> None:  # noqa: N802 - 覆写 BaseHTTPRequestHandler 约定命名
        parsed = urlparse(self.path)
        if parsed.path != "/products/search":
            self._send_json(404, {"error": {"code": "NOT_FOUND", "message": "not found"}})
            return

        query = parse_qs(parsed.query, keep_blank_values=True)
        keyword = self._first(query, "keyword")
        limit = self._first(query, "limit")

        try:
            result = self.service.search(keyword, limit)
        except ValidationError as exc:
            self._send_json(400, exc.to_dict())
            return

        self._send_json(200, result.response.to_dict())

    def do_POST(self) -> None:  # noqa: N802
        self._send_json(405, {"error": {"code": "METHOD_NOT_ALLOWED", "message": "method not allowed"}})

    do_PUT = do_POST  # noqa: N815
    do_DELETE = do_POST  # noqa: N815
    do_PATCH = do_POST  # noqa: N815

    # ------------------------------------------------------------------ #
    # 辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def _first(query: dict, key: str) -> Optional[str]:
        values = query.get(key)
        if not values:
            return None
        return values[0]

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        # 压测/测试时静默默认访问日志，减少噪声
        return
