"""pytest 夹具与路径配置。

将 src 目录加入 sys.path，使测试可直接 ``import product_search``。
所有夹具均基于内存实现，不依赖真实数据库与网络。
"""

from __future__ import annotations

import os
import sys

import pytest

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from product_search.models import Product  # noqa: E402
from product_search.repository import ProductRepository  # noqa: E402
from product_search.service import ProductSearchService  # noqa: E402


@pytest.fixture
def sample_products() -> list[Product]:
    """覆盖各 AC 所需形态的样本商品集。"""
    return [
        Product.of(1, "无线蓝牙耳机", "19.9", 100),
        Product.of(2, "ABC 音箱", "0.005", 5),
        Product.of(3, "abc 音箱", "1234.567", 0),
        Product.of(4, "测试商品A", "10.00", 7),
        Product.of(5, "测试商品B", "0.10", 8),
        Product.of(6, "a_c 特殊符号", "1.00", 1),
        Product.of(7, "百分%号商品", "2.50", 2),
        Product.of(8, "普通商品", "3.00", 3),
        Product.of(9, "single'quote", "4.00", 4),
    ]


@pytest.fixture
def service(sample_products: list[Product]) -> ProductSearchService:
    """基于样本商品的服务实例。"""
    return ProductSearchService(ProductRepository(sample_products))
