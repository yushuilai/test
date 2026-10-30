"""数据层：商品仓储（内存实现 + 倒排索引）。

内存实现模拟数据库职责：持有商品全集，search_by_name 在「数据层」完成
大小写不敏感子串匹配与稳定排序，服务层不做全表加载后过滤。

性能策略（满足 P95 < 100ms 且零外部依赖）：
- 构建 char 级与 bigram 级倒排索引，将候选集从 O(N) 全表扫描降为
  O(候选集) 校验，避免 Python 层对 10 万条做线性遍历（GIL 下并发会被放大）。
- 匹配语义仍为「大小写不敏感子串包含」，% 与 _ 按字面字符处理（索引按
  原始字符建立，天然不做 LIKE 通配符解释）。

匹配语义（与需求一致）：
- 大小写不敏感的子串包含（name.lower() 包含 keyword.lower()）
- % 与 _ 一律按字面字符处理，不解释为 LIKE 通配符

当后端替换为真实数据库时，应使用参数化 LIKE 并配合 escape_like 转义，
例如：WHERE lower(name) LIKE %{escaped}% ESCAPE '\\'（需 name 函数索引或
pg_trgm GIN 索引支撑前导通配符的性能，详见 review_report 的 P1 建议）。
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from product_search.models import Product


def escape_like(value: str) -> str:
    """将关键字中的 LIKE 通配符与转义符转义为字面字符。

    供 SQL LIKE 路径使用：先转义反斜杠本身，再转义 % 与 _。
    例如 "a_c" -> "a\\_c"，"%25%" 中的 "%" -> "\\%"。
    内存实现不依赖该函数（Python ``in`` 天然字面匹配），但保留以对齐 SQL 语义。
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ProductRepository:
    """商品仓储（内存实现，带 char/bigram 倒排索引）。"""

    def __init__(self, products: Sequence[Product] | None = None) -> None:
        self._products: List[Product] = list(products or [])
        # 预置稳定排序：name 升序、name 相同按 id 升序（与响应排序约定一致）
        self._products.sort(key=lambda p: (p.name, p.id))
        # 预计算小写名，匹配时避免反复 lower()，同时保证大小写不敏感
        self._names_lower: List[str] = [p.name.lower() for p in self._products]
        # char -> 命中位置列表；bigram -> 命中位置列表（均按位置升序）
        self._char_index: Dict[str, List[int]] = {}
        self._bigram_index: Dict[str, List[int]] = {}
        self._build_index()

    # ------------------------------------------------------------------ #
    # 索引构建
    # ------------------------------------------------------------------ #
    def _build_index(self) -> None:
        self._char_index.clear()
        self._bigram_index.clear()
        for pos, name_lower in enumerate(self._names_lower):
            seen_chars = set()
            seen_bigrams = set()
            for i, ch in enumerate(name_lower):
                if ch not in seen_chars:
                    seen_chars.add(ch)
                    self._char_index.setdefault(ch, []).append(pos)
                if i + 1 < len(name_lower):
                    bigram = name_lower[i : i + 2]
                    if bigram not in seen_bigrams:
                        seen_bigrams.add(bigram)
                        self._bigram_index.setdefault(bigram, []).append(pos)

    def add(self, product: Product) -> None:
        """追加商品并重建索引（维持排序与索引一致性）。"""
        self._products.append(product)
        self._products.sort(key=lambda p: (p.name, p.id))
        self._names_lower = [p.name.lower() for p in self._products]
        self._build_index()

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def _candidate_positions(self, keyword_lower: str) -> List[int]:
        """返回「可能包含 keyword」的商品位置候选集（升序）。

        优先选取 keyword 中命中面最窄（列表最短）的 bigram；单字符退化为
        char 索引。若某 bigram 不在索引中，则整词必无命中，返回空。
        """
        n = len(keyword_lower)
        if n >= 2:
            best: List[int] | None = None
            for i in range(n - 1):
                positions = self._bigram_index.get(keyword_lower[i : i + 2])
                if positions is not None and (best is None or len(positions) < len(best)):
                    best = positions
            return best if best is not None else []
        if n == 1:
            return self._char_index.get(keyword_lower, [])
        return []

    def search_by_name(self, keyword: str, limit: int) -> Tuple[List[Product], int]:
        """按商品名做大小写不敏感子串匹配，返回 (前 limit 条已排序结果, 命中总数)。

        keyword 已由服务层归一化（trim 后非空）；limit 已钳制到 [1, 100]。
        % 与 _ 在此按字面字符处理。
        """
        kw = keyword.lower()
        candidates = self._candidate_positions(kw)
        matched: List[Product] = [
            self._products[pos]
            for pos in candidates
            if kw in self._names_lower[pos]
        ]
        # 候选集按位置升序（等价于 (name, id) 升序），matched 天然有序；
        # 显式再排一次以防御未来变更破坏不变量，成本为 O(k log k)。
        matched.sort(key=lambda p: (p.name, p.id))
        total = len(matched)
        return matched[:limit], total
