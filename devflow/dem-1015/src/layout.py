"""Responsive layout rules for the login card (AC-DEM-1015-010)."""

from __future__ import annotations

from typing import Tuple

VIEWPORTS: Tuple[int, ...] = (360, 768, 1440, 1920)
TAP_TARGET_MIN_PX = 44
SIDE_MARGIN_PX = 16
MAX_CARD_WIDTH_PX = 420
BUTTON_HEIGHT_PX = 48


def card_width_for(viewport: int) -> int:
    """Return the adaptive card width that never exceeds the safe margins."""
    if viewport <= 0:
        return 0
    return min(MAX_CARD_WIDTH_PX, viewport - 2 * SIDE_MARGIN_PX)


def has_horizontal_scroll(viewport: int) -> bool:
    """Return True when card width plus margins exceeds the viewport."""
    return card_width_for(viewport) + 2 * SIDE_MARGIN_PX > viewport


def tap_target_height() -> int:
    """Return the login button tap height (>= 44 px per the spec)."""
    return BUTTON_HEIGHT_PX
