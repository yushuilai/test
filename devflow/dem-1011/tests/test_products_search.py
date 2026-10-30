"""GET /products/search 的 pytest 回归基线。

覆盖 req_spec 全部验收标准 AC-001 ~ AC-012。除 HTTP 层用例外均为
服务层/仓储层直接调用，不依赖真实数据库与外部网络。
"""

from __future__ import annotations

import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

import pytest

from product_search.models import Product, format_price
from product_search.repository import ProductRepository, escape_like
from product_search.router import ProductSearchHandler
from product_search.service import ProductSearchService, ValidationError

# --------------------------------------------------------------------------- #
# 服务层：AC-001 ~ AC-009
# --------------------------------------------------------------------------- #


def test_ac_001_normal_hit_fields_and_total(service: ProductSearchService) -> None:
    """正常命中：items 含目标商品，单项恰为四键，total 等于全量命中数。"""
    result = service.search("耳机", "20")
    body = result.response.to_dict()

    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert set(item.keys()) == {"id", "name", "price", "stock"}
    assert item["name"] == "无线蓝牙耳机"
    assert item["id"] == 1


def test_ac_002_keyword_missing_does_not_touch_repo() -> None:
    """keyword 缺失 -> 400 INVALID_KEYWORD，且不触达数据层。"""
    repo = mock.Mock(spec=ProductRepository)
    svc = ProductSearchService(repo)
    with pytest.raises(ValidationError) as exc:
        svc.search(None)
    assert exc.value.code == "INVALID_KEYWORD"
    assert exc.value.message
    repo.search_by_name.assert_not_called()


def test_ac_002_keyword_empty_string(service: ProductSearchService) -> None:
    """keyword 空串 -> 400 INVALID_KEYWORD。"""
    with pytest.raises(ValidationError) as exc:
        service.search("")
    assert exc.value.code == "INVALID_KEYWORD"


def test_ac_002_keyword_whitespace(service: ProductSearchService) -> None:
    """keyword 纯空白 -> 400 INVALID_KEYWORD。"""
    with pytest.raises(ValidationError) as exc:
        service.search("   ")
    assert exc.value.code == "INVALID_KEYWORD"


def test_ac_002_keyword_overlength_128(service: ProductSearchService) -> None:
    """keyword 长度 129 -> 400 INVALID_KEYWORD（超长拒绝而非截断）。"""
    with pytest.raises(ValidationError) as exc:
        service.search("x" * 129)
    assert exc.value.code == "INVALID_KEYWORD"
    # 边界：恰好 128 合法
    assert service.search("x" * 128).response.total == 0


def test_ac_003_price_rounding_half_up() -> None:
    """price 输出两位小数（ROUND_HALF_UP，字符串类型）。"""
    repo = ProductRepository([
        Product.of(1, "价格测试A", "19.9", 1),
        Product.of(2, "价格测试B", "0.005", 1),
        Product.of(3, "价格测试C", "1234.567", 1),
    ])
    svc = ProductSearchService(repo)
    body = svc.search("价格测试", "20").response.to_dict()

    prices = [item["price"] for item in body["items"]]
    assert prices == ["19.90", "0.01", "1234.57"]
    for p in prices:
        assert isinstance(p, str)
        # 小数位不超过 2 位
        assert len(p.split(".")[1]) == 2


def test_ac_004_no_result_empty_body(service: ProductSearchService) -> None:
    """无结果 -> 200，响应体严格等于 {items:[], total:0}（非 404）。"""
    body = service.search("zzz_not_exist").response.to_dict()
    assert body == {"items": [], "total": 0}


def test_ac_005_limit_upper_clamp() -> None:
    """limit 超上限（101/1000）-> 钳制到 100，total 不受 limit 影响。"""
    products = [Product.of(i, f"测试商品{i:04d}", "1.00", 1) for i in range(1, 151)]
    svc = ProductSearchService(ProductRepository(products))

    for limit in ("101", "1000"):
        body = svc.search("测试", limit).response.to_dict()
        assert len(body["items"]) == 100
        assert body["total"] == 150


def test_ac_006_limit_boundary() -> None:
    """limit=0/-5 钳制到 1；limit=1 保持 1；limit=abc 返回 400。"""
    products = [Product.of(i, f"测试商品{i:04d}", "1.00", 1) for i in range(1, 6)]
    svc = ProductSearchService(ProductRepository(products))

    assert len(svc.search("测试", "0").response.items) == 1
    assert len(svc.search("测试", "-5").response.items) == 1
    assert len(svc.search("测试", "1").response.items) == 1

    with pytest.raises(ValidationError) as exc:
        svc.search("测试", "abc")
    assert exc.value.code == "INVALID_LIMIT"
    assert exc.value.message


def test_ac_007_case_insensitive_and_special_chars(service: ProductSearchService) -> None:
    """大小写不敏感；% _ ' 按字面处理，不解释为通配符。"""
    # 大小写不敏感：abc 命中 ABC 音箱 / abc 音箱
    body = service.search("abc").response.to_dict()
    names = sorted(item["name"] for item in body["items"])
    assert names == ["ABC 音箱", "abc 音箱"]
    assert body["total"] == 2

    # _ 不解释为单字符通配符：仅命中字面含 a_c 的商品
    body = service.search("a_c").response.to_dict()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "a_c 特殊符号"

    # % 按字面处理：不返回全量数据
    body = service.search("%").response.to_dict()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "百分%号商品"

    # 单引号按字面处理
    body = service.search("'").response.to_dict()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "single'quote"


def test_ac_008_default_limit() -> None:
    """未传 limit -> 默认 20；命中 15 条时返回 15。"""
    products = [Product.of(i, f"默认限制商品{i:04d}", "1.00", 1) for i in range(1, 16)]
    svc = ProductSearchService(ProductRepository(products))
    body = svc.search("默认限制商品").response.to_dict()
    assert len(body["items"]) == 15
    assert body["total"] == 15


def test_ac_009_stable_order() -> None:
    """同名/匹配度相同 -> 两次请求顺序一致（name 升序、name 同按 id 升序）。"""
    repo = ProductRepository([
        Product.of(2, "同名商品", "1.00", 1),
        Product.of(1, "同名商品", "1.00", 1),
        Product.of(3, "同名商品X", "1.00", 1),
    ])
    svc = ProductSearchService(repo)

    first = [i.id for i in svc.search("同名商品").response.items]
    second = [i.id for i in svc.search("同名商品").response.items]
    assert first == second
    assert first == [1, 2, 3]


def test_escape_like_literal() -> None:
    """escape_like 将 % _ \\ 转义为字面字符（SQL LIKE 路径）。"""
    assert escape_like("a_c") == "a\\_c"
    assert escape_like("100%") == "100\\%"
    assert escape_like(r"a\b") == "a\\\\b"


# --------------------------------------------------------------------------- #
# 依赖与性能：AC-010 / AC-011
# --------------------------------------------------------------------------- #

FORBIDDEN_IMPORTS = [
    "flask", "fastapi", "django", "sqlalchemy", "requests",
    "redis", "elasticsearch", "meilisearch", "pymongo", "pymysql",
    "psycopg2", "aiohttp", "starlette", "uvicorn",
]


def test_ac_010_no_new_runtime_deps() -> None:
    """运行时源码不引入第三方依赖（仅标准库 + 现有框架占位）。"""
    src_root = os.path.join(os.path.dirname(__file__), "..", "src")
    py_files = []
    for dirpath, _dirs, files in os.walk(src_root):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(dirpath, f))
    assert py_files, "未找到任何源文件"

    for path in py_files:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped.startswith(("import ", "from ")):
                    continue
                for dep in FORBIDDEN_IMPORTS:
                    assert dep not in stripped, f"{path} 引入了禁用依赖 {dep}"


def test_ac_011_perf_smoke_under_100ms() -> None:
    """性能冒烟：10 万条热态下单词搜索均值 < 100ms（回归护栏，非完整压测）。"""
    import time

    from app import generate_products

    products = generate_products(100000)
    svc = ProductSearchService(ProductRepository(products))

    # 预热 30 次不计入统计
    for _ in range(30):
        svc.search("无线", "20")

    latencies = []
    for _ in range(15):
        t0 = time.perf_counter()
        svc.search("无线", "20")
        latencies.append((time.perf_counter() - t0) * 1000)

    mean_ms = sum(latencies) / len(latencies)
    assert mean_ms < 100, f"平均耗时 {mean_ms:.2f}ms 超过 100ms"


# --------------------------------------------------------------------------- #
# HTTP 层：状态码与响应体（localhost 内进程，无外部网络）
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def http_base_url() -> str:
    service = ProductSearchService(
        ProductRepository([
            Product.of(1, "无线蓝牙耳机", "19.9", 100),
            Product.of(2, "百分%号商品", "2.50", 2),
        ])
    )
    ProductSearchHandler.service = service
    server = ThreadingHTTPServer(("127.0.0.1", 0), ProductSearchHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


def _get(base: str, path: str, params: dict | None = None) -> tuple[int, dict]:
    import json
    from urllib.parse import urlencode

    url = base + path
    if params is not None:
        url += "?" + urlencode(params)
    # 本地回环请求禁用环境代理，避免走 HTTP_PROXY 造成额外延迟
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def test_http_status_codes_and_bodies(http_base_url: str) -> None:
    """HTTP 层：200/400/404 状态码与错误体契约。"""
    # 200 正常命中
    status, body = _get(http_base_url, "/products/search", {"keyword": "耳机", "limit": "20"})
    assert status == 200
    assert body["total"] == 1

    # 400 keyword 空串（%20%20 -> 纯空白）
    status, body = _get(http_base_url, "/products/search", {"keyword": "  "})
    assert status == 400
    assert body["error"]["code"] == "INVALID_KEYWORD"
    assert body["error"]["message"]

    # 400 limit 非整数
    status, body = _get(http_base_url, "/products/search", {"keyword": "耳机", "limit": "abc"})
    assert status == 400
    assert body["error"]["code"] == "INVALID_LIMIT"

    # % 解码为字面百分号，不返回全量数据
    status, body = _get(http_base_url, "/products/search", {"keyword": "%"})
    assert status == 200
    assert body["total"] == 1
    assert body["items"][0]["name"] == "百分%号商品"

    # 404 未知路径
    status, body = _get(http_base_url, "/nonexistent")
    assert status == 404


def test_http_no_result_returns_200_not_404(http_base_url: str) -> None:
    """无结果返回 200 + {items:[], total:0}，而非 404。"""
    status, body = _get(http_base_url, "/products/search", {"keyword": "zzz_not_exist"})
    assert status == 200
    assert body == {"items": [], "total": 0}


def test_http_default_limit(http_base_url: str) -> None:
    """未传 limit 时返回 200 且 items 长度不超过 20。"""
    status, body = _get(http_base_url, "/products/search", {"keyword": "耳机"})
    assert status == 200
    assert len(body["items"]) <= 20
