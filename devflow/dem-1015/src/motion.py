"""Motion configuration and reduced-motion degradation.

Micro animations must stay in the 150-400 ms range with an ease-out curve
(AC-DEM-1015-011 item 5). Under ``prefers-reduced-motion: reduce`` continuous
animation is disabled and transitions are capped at 100 ms (AC-DEM-1015-012).
"""

from __future__ import annotations

MOTION_MIN_MS = 150
MOTION_MAX_MS = 400
REDUCED_MOTION_MAX_MS = 100

_EASE_OUT_EASINGS = ("ease-out", "ease-out-quad", "cubic-bezier(0.22, 1, 0.36, 1)")


def is_valid_motion_duration(duration_ms: int) -> bool:
    """Return True when ``duration_ms`` is inside the 150-400 ms window."""
    return MOTION_MIN_MS <= duration_ms <= MOTION_MAX_MS


def is_ease_out(easing: str) -> bool:
    """Return True when the easing curve is an ease-out family curve."""
    return easing in _EASE_OUT_EASINGS


def continuous_animation_enabled(prefers_reduced_motion: bool) -> bool:
    """Return True only when the user has NOT requested reduced motion."""
    return not prefers_reduced_motion


def effective_motion_duration(prefers_reduced_motion: bool, duration_ms: int) -> int:
    """Return the duration after applying the reduced-motion preference."""
    if prefers_reduced_motion:
        return min(duration_ms, REDUCED_MOTION_MAX_MS)
    return duration_ms
