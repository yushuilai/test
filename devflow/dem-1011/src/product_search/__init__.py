"""商品搜索接口包。

提供 GET /products/search 的完整纵向切片：
- models:      领域模型与序列化约束（items 单项白名单 id/name/price/stock）
- repository:  数据层（内存实现，模拟数据库，支持 LIKE 字面转义）
- service:     业务逻辑（入参校验、limit 钳制、price 舍入）
- router:      标准库 HTTP 处理器（无第三方运行时依赖）
"""

from product_search.service import ProductSearchService, ValidationError
from product_search.repository import ProductRepository
from product_search.models import Product, ProductSearchItem, ProductSearchResponse

__all__ = [
    "Product",
    "ProductSearchItem",
    "ProductSearchResponse",
    "ProductRepository",
    "ProductSearchService",
    "ValidationError",
]
