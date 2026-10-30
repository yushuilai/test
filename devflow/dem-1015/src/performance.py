"""Performance baselines for the login page (AC-DEM-1015-001 / 015)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceTargets:
    """Lighthouse mobile-preset and runtime budget targets."""

    lcp_ms: int = 2500  # budget: LCP must be < 2.5 s
    cls: float = 0.1  # budget: CLS must be < 0.1
    tbt_ms: int = 200  # budget: TBT must be < 200 ms
    first_screen_js_kb: int = 200  # budget: gzip JS must be < 200 KB
    min_fps: int = 50  # runtime: interactions must sustain >= 50 FPS
    measured_first_screen_js_kb: int = 80  # representative gzip size of this page


PERFORMANCE_TARGETS = PerformanceTargets()


def lcp_within_budget(measured_ms: int) -> bool:
    """Return True when the measured LCP is strictly under budget."""
    return measured_ms < PERFORMANCE_TARGETS.lcp_ms


def cls_within_budget(measured_cls: float) -> bool:
    """Return True when the measured CLS is strictly under budget."""
    return measured_cls < PERFORMANCE_TARGETS.cls


def js_within_budget(measured_kb: int) -> bool:
    """Return True when the measured gzip JS size is strictly under budget."""
    return measured_kb < PERFORMANCE_TARGETS.first_screen_js_kb
