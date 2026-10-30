"""商品搜索接口 pytest 测试（demand:19 / DEM-1009）。

覆盖 req_spec 全部 AC（001~010）：
- 四条主路径：正常命中 / 空关键词 / limit 越界 / 无结果；
- 边界补充：纯空格、通配符转义（含反斜杠）、limit 非整数（abc/1.5/空串）、
  total 与 limit 关系、price 舍入、SQL 注入字面量、稳定排序、性能（单独标记）。

性能用例（test_ac_007）使用 ``@pytest.mark.perf`` 标记，可用
``pytest -m "not perf"`` 在功能 CI 中跳过。
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

from src.api import search_products_endpoint
from src.errors import INVALID_KEYWORD, INVALID_LIMIT
from src.schemas import Product
from src.service import (
    MAX_KEYWORD_LENGTH,
    build_like_pattern,
    escape_like,
    search_products,
)
from src.store import ProductStore


# --------------------------------------------------------------------------- #
# 工具与夹具
# --------------------------------------------------------------------------- #
def _store(*rows) -> ProductStore:
    """rows: (id, name, price, stock) 元组。"""
    return ProductStore(
        [Product(id=r[0], name=r[1], price=r[2], stock=r[3]) for r in rows]
    )


class _ExplodingStore:
    """一旦被查询即失败，用于断言「非法请求不触达数据层」。"""

    def search(self, keyword, limit):  # pragma: no cover - 仅防御
        raise AssertionError("store must not be queried for invalid keyword")


@pytest.fixture
def iphone_store() -> ProductStore:
    return _store(
        (1, "iPhone 15 Pro", 2.675, 10),
        (2, "iPhone Charger", 19.99, 5),
        (3, "Samsung Galaxy S24", 799.0, 3),
        (4, "MacBook Air", 999.0, 2),
    )


@pytest.fixture
def many_store() -> ProductStore:
    return _store(*[(i, f"match-item-{i:03d}", float(i), i % 50) for i in range(200)])


# --------------------------------------------------------------------------- #
# AC-001 正常命中：大小写不敏感 + 字段白名单 + price 两位小数 + total 全量
# --------------------------------------------------------------------------- #
def test_ac_001_normal_hit_fields_and_case_insensitive(iphone_store) -> None:
    status, body = search_products_endpoint(keyword="iphone", store=iphone_store)
    assert status == 200

    names = [item["name"] for item in body["items"]]
    assert names == ["iPhone 15 Pro", "iPhone Charger"]

    for item in body["items"]:
        assert set(item.keys()) == {"id", "name", "price", "stock"}
        assert re.fullmatch(r"\d+\.\d{2}", item["price"]), item["price"]

    assert body["total"] == 2


# --------------------------------------------------------------------------- #
# AC-002 空关键词：缺失 / 空串 / 纯空白 -> 400，且不触达数据层
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("keyword", [None, "", "   ", "\t\n"])
def test_ac_002_empty_keyword_400_no_query(keyword) -> None:
    status, body = search_products_endpoint(
        keyword=keyword, store=_ExplodingStore()
    )
    assert status == 400
    assert body["code"] == INVALID_KEYWORD


# --------------------------------------------------------------------------- #
# AC-003 limit 钳制：缺失/0/-5/1/100/101/1000 与返回条数 = min(total, limit)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "limit,expected",
    [(None, 20), (0, 1), (-5, 1), (1, 1), (100, 100), (101, 100), (1000, 100)],
)
def test_ac_003_limit_clamping(many_store, limit, expected) -> None:
    status, body = search_products_endpoint(
        keyword="match-item", limit=limit, store=many_store
    )
    assert status == 200
    assert body["total"] == 200
    assert len(body["items"]) == min(200, expected)


@pytest.mark.parametrize("limit", ["abc", "1.5", "", "  ", True])
def test_ac_003_limit_non_integer_400(many_store, limit) -> None:
    status, body = search_products_endpoint(
        keyword="match-item", limit=limit, store=many_store
    )
    assert status == 400
    assert body["code"] == INVALID_LIMIT


# --------------------------------------------------------------------------- #
# AC-004 total 不受 limit 影响
# --------------------------------------------------------------------------- #
def test_ac_004_total_independent_of_limit() -> None:
    store = _store(*[(i, "x-phone", 1.0, 1) for i in range(25)])
    status, body = search_products_endpoint(keyword="x-phone", limit=20, store=store)
    assert status == 200
    assert len(body["items"]) == 20
    assert body["total"] == 25


# --------------------------------------------------------------------------- #
# AC-005 price 按 ROUND_HALF_UP 保留两位小数
# --------------------------------------------------------------------------- #
def test_ac_005_price_rounding() -> None:
    store = _store(
        (1, "round-a", 2.675, 1),
        (2, "round-b", 0.005, 1),
        (3, "round-c", 10, 1),
    )
    status, body = search_products_endpoint(keyword="round", store=store)
    assert status == 200
    by_name = {item["name"]: item["price"] for item in body["items"]}
    assert by_name == {"round-a": "2.68", "round-b": "0.01", "round-c": "10.00"}


# --------------------------------------------------------------------------- #
# AC-006 错误响应 envelope 含 code 与 message
# --------------------------------------------------------------------------- #
def test_ac_006_error_envelope_shape() -> None:
    status, body = search_products_endpoint(keyword="", store=_store())
    assert status == 400
    assert set(body.keys()) == {"code", "message"}
    assert body["code"] == INVALID_KEYWORD
    assert isinstance(body["message"], str) and body["message"]


# --------------------------------------------------------------------------- #
# AC-007 性能：10 万行、预热 20 次、顺序请求 200 次，P95 < 100ms
# --------------------------------------------------------------------------- #
@pytest.mark.perf
def test_ac_007_performance_p95() -> None:
    n = 100_000
    products = [
        Product(id=i, name=f"product-{i:06d}", price=float(i % 1000) / 10.0, stock=i % 50)
        for i in range(n)
    ]
    store = ProductStore(products)

    def _request() -> None:
        status, body = search_products_endpoint(keyword="0001", limit=20, store=store)
        assert status == 200

    for _ in range(20):  # 预热
        _request()

    latencies_ms = []
    for _ in range(200):
        start = time.perf_counter()
        _request()
        latencies_ms.append((time.perf_counter() - start) * 1000)

    latencies_ms.sort()
    p95 = latencies_ms[int(len(latencies_ms) * 0.95) - 1]
    assert p95 < 100, f"P95 = {p95:.2f}ms"


# --------------------------------------------------------------------------- #
# AC-008 通配符转义 / 长度上限 / 反斜杠 / SQL 注入字面量
# --------------------------------------------------------------------------- #
def test_ac_008_wildcard_escape_and_length() -> None:
    store = _store(
        (1, "discount 10% off", 1.0, 1),
        (2, "under_score_item", 1.0, 1),
        (3, "normal item one", 1.0, 1),
        (4, "normal item two", 1.0, 1),
    )
    # "%" 仅命中字面包含 % 的商品，而非全表
    _, body = search_products_endpoint(keyword="%", store=store)
    assert body["total"] == 1
    assert [i["name"] for i in body["items"]] == ["discount 10% off"]

    # "_" 仅命中字面下划线
    _, body = search_products_endpoint(keyword="_", store=store)
    assert body["total"] == 1
    assert [i["name"] for i in body["items"]] == ["under_score_item"]

    # 超长 keyword -> 400
    status, body = search_products_endpoint(keyword="a" * 101, store=store)
    assert status == 400
    assert body["code"] == INVALID_KEYWORD


def test_ac_008_backslash_literal() -> None:
    store = _store((1, "back\\slash", 1.0, 1), (2, "plain", 1.0, 1))
    _, body = search_products_endpoint(keyword="\\", store=store)
    assert body["total"] == 1
    assert [i["name"] for i in body["items"]] == ["back\\slash"]


def test_ac_008_sql_injection_literal() -> None:
    store = _store((1, "apple", 1.0, 1), (2, "banana", 1.0, 1))
    before = len(store)
    payload = "'; DROP TABLE products; --"
    status, body = search_products_endpoint(keyword=payload, store=store)
    assert status == 200
    assert body["items"] == []
    assert body["total"] == 0
    assert len(store) == before


def test_ac_008_escape_like_order() -> None:
    assert escape_like("\\") == "\\\\"
    assert escape_like("%") == "\\%"
    assert escape_like("_") == "\\_"
    assert escape_like("a\\b%c_d") == "a\\\\b\\%c\\_d"
    assert build_like_pattern("a_b") == "%a\\_b%"


# --------------------------------------------------------------------------- #
# AC-009 稳定排序（name ASC, id ASC）
# --------------------------------------------------------------------------- #
def test_ac_009_stable_order() -> None:
    store = _store(
        (3, "apple", 1.0, 1),
        (1, "Apple", 1.0, 1),
        (2, "banana", 1.0, 1),
    )
    first = search_products_endpoint(keyword="a", store=store)[1]["items"]
    second = search_products_endpoint(keyword="a", store=store)[1]["items"]
    assert [i["id"] for i in first] == [1, 3, 2]  # "Apple" < "apple" < "banana"
    assert first == second


# --------------------------------------------------------------------------- #
# AC-004 补充：无结果路径（keyword 无命中）
# --------------------------------------------------------------------------- #
def test_ac_004_no_result(iphone_store) -> None:
    status, body = search_products_endpoint(keyword="zzz-not-found", store=iphone_store)
    assert status == 200
    assert body["items"] == []
    assert body["total"] == 0


# --------------------------------------------------------------------------- #
# AC-010 测试集完整性（四条主路径 + 边界用例均已存在）
# --------------------------------------------------------------------------- #
def test_ac_010_suite_completeness() -> None:
    src = Path(__file__).read_text(encoding="utf-8")
    required = [
        # 四条主路径
        "test_ac_001_normal_hit_fields_and_case_insensitive",
        "test_ac_002_empty_keyword_400_no_query",
        "test_ac_003_limit_clamping",
        "test_ac_004_no_result",
        # 边界补充
        "test_ac_003_limit_non_integer_400",
        "test_ac_004_total_independent_of_limit",
        "test_ac_005_price_rounding",
        "test_ac_008_wildcard_escape_and_length",
        "test_ac_008_backslash_literal",
        "test_ac_008_sql_injection_literal",
        "test_ac_009_stable_order",
    ]
    missing = [name for name in required if f"def {name}(" not in src]
    assert not missing, f"missing test functions: {missing}"
