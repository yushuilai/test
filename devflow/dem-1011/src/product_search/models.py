"""领域模型与序列化约束。

items 单项严格白名单为 id/name/price/stock 四个键，防止成本价、内部 SKU 等
非白名单字段泄漏。price 统一以字符串输出（两位小数，ROUND_HALF_UP），
原因是 JSON number 无法保留尾零（19.90 会被序列化为 19.9），string 才能
满足「price 固定两位小数」与「列表页直接渲染」两个约束。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List


# 两位小数金额的量化基准
_TWO_PLACES = Decimal("0.01")


def to_decimal(value: Any) -> Decimal:
    """将任意数值转为 Decimal。

    对 float 一律先转 str 再转 Decimal，避免二进制浮点误差
    （例如 0.005 直接 Decimal(0.005) 会得到 0.005000000000000000104...）。
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        # bool 是 int 子类，需先排除，避免 True/False 被当作价格
        raise ValueError(f"price 不能是布尔值: {value!r}")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value)
    raise ValueError(f"不支持的 price 类型: {type(value)!r}")


def format_price(value: Any) -> str:
    """按 ROUND_HALF_UP 保留两位小数并输出字符串。

    19.9 -> "19.90"; 0.005 -> "0.01"; 1234.567 -> "1234.57"。
    """
    rounded = to_decimal(value).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
    return format(rounded, "f")


@dataclass(frozen=True)
class Product:
    """商品实体（数据层内部表示）。"""

    id: int
    name: str
    price: Decimal
    stock: int

    def __post_init__(self) -> None:
        # price 统一归一化为 Decimal，保证后续计算一致
        object.__setattr__(self, "price", to_decimal(self.price))

    @classmethod
    def of(cls, id: int, name: str, price: Any, stock: int) -> "Product":
        """便捷构造：接受任意数值类型 price。"""
        return cls(id=id, name=name, price=to_decimal(price), stock=stock)


@dataclass(frozen=True)
class ProductSearchItem:
    """搜索命中项（对外输出，白名单四键）。"""

    id: int
    name: str
    price: str
    stock: int

    def to_dict(self) -> Dict[str, Any]:
        """严格输出 id/name/price/stock 四键，无多余字段。"""
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "stock": self.stock,
        }


@dataclass(frozen=True)
class ProductSearchResponse:
    """搜索响应体 {items: [...], total}。"""

    items: List[ProductSearchItem] = field(default_factory=list)
    total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
        }
