"""服务入口：启动 GET /products/search 的 HTTP 服务。

用法：
    python app.py [--host 127.0.0.1] [--port 8080] [--seed 100000]

零第三方运行时依赖，仅标准库。默认 seed 0（空库），便于测试；压测时
可传 --seed 100000 预置 10 万条商品。
"""

from __future__ import annotations

import argparse
import random
from http.server import ThreadingHTTPServer
from typing import List, Sequence

from product_search.models import Product
from product_search.repository import ProductRepository
from product_search.router import ProductSearchHandler
from product_search.service import ProductSearchService


def generate_products(count: int, seed: int = 42) -> Sequence[Product]:
    """生成 ``count`` 条商品，名称由常见词组合，保证存在可命中的子串。"""
    rng = random.Random(seed)
    adjectives = ["无线", "蓝牙", "智能", "便携", "高保真", "降噪", "经典", "迷你"]
    nouns = ["耳机", "音箱", "键盘", "鼠标", "显示器", "充电器", "摄像头", "手表"]
    products: List[Product] = []
    for i in range(1, count + 1):
        name = f"{rng.choice(adjectives)}{rng.choice(nouns)}-{i:06d}"
        price = round(rng.uniform(0.005, 9999.99), 3)
        stock = rng.randint(0, 1000)
        products.append(Product.of(id=i, name=name, price=price, stock=stock))
    return products


def main() -> None:
    parser = argparse.ArgumentParser(description="商品搜索接口服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--seed", type=int, default=0, help="预置商品条数")
    args = parser.parse_args()

    repo = ProductRepository(generate_products(args.seed))
    service = ProductSearchService(repo)
    ProductSearchHandler.service = service

    server = ThreadingHTTPServer((args.host, args.port), ProductSearchHandler)
    print(f"listening on http://{args.host}:{args.port} (seeded {args.seed} products)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
