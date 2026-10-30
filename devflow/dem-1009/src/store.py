"""商品数据访问层（内存实现）。

真实项目中该层由 ORM/数据库替换（参数化查询、LIKE 与 ESCAPE 在 SQL 侧执行）。
此处用内存列表给出等价语义，供 service 单测与性能用例复用：

- 匹配语义等价于 ``name LIKE '%keyword%'``（不区分大小写）；
- ``keyword`` 传入的是「已校验、已 strip 的原始关键词」，匹配按字面包含进行，
  因此 ``%`` / ``_`` 只会匹配字面字符（等价于 SQL 侧先做通配符转义）。
- 为性能，构造时预计算 ``casefold`` 后的小写名称，避免每次查询重复小写化。
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from .schemas import Product


class ProductStore:
    """内存商品仓库。"""

    def __init__(self, products: Sequence[Product]) -> None:
        self._products: List[Product] = list(products)
        self._lower_names: List[str] = [p.name.casefold() for p in self._products]

    def search(self, keyword: str, limit: int) -> Tuple[List[Product], int]:
        """返回 (匹配项[已排序并截断到 limit], 全量命中总数)。

        排序：``ORDER BY name ASC, id ASC``，保证结果稳定。
        """
        needle = keyword.casefold()
        matched: List[Product] = []
        for lower_name, product in zip(self._lower_names, self._products):
            if needle in lower_name:
                matched.append(product)

        total = len(matched)
        matched.sort(key=lambda p: (p.name, p.id))
        return matched[:limit], total

    def __len__(self) -> int:
        return len(self._products)
