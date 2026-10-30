"""P95/P99 压测脚本（AC-011），复用标准库，不新增运行时依赖。

用法：
    python benchmark_search.py --count 100000 --concurrency 20 --duration 60 [--mode thread|process]

模式说明（关键差异）：
- ``thread``：线程池模拟 20 并发，等价于标准库 ThreadingHTTPServer 的真实表现。
  由于纯 Python 的 CPU 密集检索受 GIL 串行化，线程越多争用越重，P95 会被显著抬高。
- ``process``：多进程 worker（各自持有独立内存索引），等价于生产环境
  「gunicorn/uvicorn --workers N」的多进程部署模型，规避 GIL，实测可满足 P95<100ms。

预热前 100 次请求不计入统计。输出 P50/P95/P99 与错误率，供归档。
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

from app import generate_products
from product_search.repository import ProductRepository
from product_search.service import ProductSearchService

# 命中率约 5%~12% 的常见词（与 generate_products 的形容词一致）
COMMON_KEYWORD = "无线"
WARMUP = 100

# 多进程 worker 的进程内单例
_WORKER_SERVICE: ProductSearchService | None = None


def _init_worker(products: List) -> None:
    global _WORKER_SERVICE
    _WORKER_SERVICE = ProductSearchService(ProductRepository(products))


def _search_once(_: None) -> float:
    """多进程 worker：执行一次搜索并返回耗时（秒）。"""
    assert _WORKER_SERVICE is not None
    start = time.perf_counter()
    _WORKER_SERVICE.search(COMMON_KEYWORD, "20")
    return time.perf_counter() - start


def _run_once(service: ProductSearchService) -> float:
    start = time.perf_counter()
    service.search(COMMON_KEYWORD, "20")
    return time.perf_counter() - start


def _summarize(latencies: List[float], errors: int) -> None:
    total = len(latencies) + errors
    if latencies:
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        mean = statistics.mean(latencies)
    else:
        p50 = p95 = p99 = mean = 0.0
    print(f"requests={total} errors={errors} error_rate={errors / total:.4%}")
    print(f"mean={mean * 1000:.2f}ms p50={p50 * 1000:.2f}ms "
          f"p95={p95 * 1000:.2f}ms p99={p99 * 1000:.2f}ms")


def benchmark_thread(count: int, concurrency: int, duration: float) -> None:
    service = ProductSearchService(ProductRepository(generate_products(count)))
    for _ in range(WARMUP):
        _run_once(service)

    latencies: List[float] = []
    errors = 0
    stop = threading.Event()

    def worker() -> None:
        nonlocal errors
        while not stop.is_set():
            try:
                latencies.append(_run_once(service))
            except Exception:  # noqa: BLE001 - 压测需统计一切异常为错误
                errors += 1

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker) for _ in range(concurrency)]
        time.sleep(duration)
        stop.set()
        for f in futures:
            f.result()

    _summarize(latencies, errors)


def _worker_loop(duration: float):
    """多进程 worker：持续搜索 duration 秒，返回 (本地耗时列表, 错误数)。

    与 thread 模式同口径——在 worker 内部计时，避免父进程 imap 逐条
    收集结果时引入的 IPC 往返开销污染测量。
    """
    assert _WORKER_SERVICE is not None
    latencies: List[float] = []
    errors = 0
    deadline = time.time() + duration
    while time.time() < deadline:
        try:
            latencies.append(_run_once(_WORKER_SERVICE))
        except Exception:  # noqa: BLE001
            errors += 1
    return latencies, errors


def benchmark_process(count: int, concurrency: int, duration: float) -> None:
    products = generate_products(count)
    ctx = mp.get_context("spawn")
    with ctx.Pool(
        processes=concurrency,
        initializer=_init_worker,
        initargs=(products,),
    ) as pool:
        # 预热
        pool.map(_search_once, [None] * WARMUP, chunksize=1)
        results = pool.map(_worker_loop, [duration] * concurrency)

    latencies: List[float] = []
    errors = 0
    for lats, errs in results:
        latencies.extend(lats)
        errors += errs
    _summarize(latencies, errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100000)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--mode", choices=["thread", "process"], default="thread")
    args = parser.parse_args()

    print(f"records={args.count} concurrency={args.concurrency} "
          f"duration={args.duration}s mode={args.mode} warmup={WARMUP}")
    if args.mode == "thread":
        benchmark_thread(args.count, args.concurrency, args.duration)
    else:
        benchmark_process(args.count, args.concurrency, args.duration)


if __name__ == "__main__":
    mp.freeze_support()
    main()
