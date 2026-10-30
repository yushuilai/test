"""领域模型与响应序列化白名单。

关键决策（因架构基线为空，按最小可用约定落地并在此固化）：
- price 的对外类型为「两位小数字符串」（如 ``"2.68"`` / ``"10.00"``），
  使用 ``Decimal(str(value))`` 按 ROUND_HALF_UP 量化，从根上消除浮点尾差。
- ``Product`` 含内部字段 ``cost``，仅用于验证序列化白名单不会将其透出。
- 响应体仅包含 ``id`` / ``name`` / ``price`` / ``stock`` 与 ``total``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List


def round_price(value: float) -> str:
    """将价格按 ROUND_HALF_UP 保留两位小数，返回定长字符串。

    使用 ``Decimal(str(value))`` 而非 ``Decimal(value)``，避免 float 的二进制
    表示（如 2.675 实为 2.674999...）被直接带入量化。
    """
    quantized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(quantized, "f")


@dataclass(frozen=True)
class Product:
    """商品内部模型（含不应透出的成本字段 cost）。"""

    id: int
    name: str
    price: float
    stock: int
    cost: float = 0.0


@dataclass(frozen=True)
class ProductSearchItem:
    """搜索命中项的对外视图（白名单：id/name/price/stock）。"""

    id: int
    name: str
    price: str
    stock: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "stock": self.stock,
        }


@dataclass(frozen=True)
class ProductSearchResponse:
    """搜索响应：items + 全量命中数 total。"""

    items: List[ProductSearchItem] = field(default_factory=list)
    total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
        }
