"""Responsive layout rules for the login card (AC-DEM-1015-010).

All numbers are expressed here so the CSS breakpoints and the tests share one
source of truth. The soft-keyboard behaviour is modelled as a geometric proxy:
an input is "occluded" when its bottom edge falls below the visible viewport once
the keyboard is subtracted, and the page must provide enough scroll padding to
bring it back into view.
"""

from __future__ import annotations

from typing import Tuple

VIEWPORTS: Tuple[int, ...] = (360, 768, 1440, 1920)

TAP_TARGET_MIN_PX = 44
SIDE_MARGIN_PX = 16
MAX_CARD_WIDTH_PX = 420
BUTTON_HEIGHT_PX = 48
INPUT_HEIGHT_PX = 48
SCROLL_PADDING_PX = 24

_BREAKPOINTS = (
    (480, "sm"),
    (768, "md"),
    (1440, "lg"),
    (1920, "xl"),
)


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


def is_tap_target_ok(height_px: int) -> bool:
    """Return True when a control meets the 44 px minimum touch target."""
    return height_px >= TAP_TARGET_MIN_PX


def breakpoint_for(viewport: int) -> str:
    """Return the layout bucket (``sm``/``md``/``lg``/``xl``) for a viewport."""
    for max_width, name in _BREAKPOINTS:
        if viewport <= max_width:
            return name
    return _BREAKPOINTS[-1][1]


def scroll_padding_bottom(keyboard_height_px: int) -> int:
    """Return the scroll padding needed so a focused input clears the keyboard."""
    return max(SCROLL_PADDING_PX, keyboard_height_px)


def is_input_occluded(
    input_top: int,
    viewport_height: int,
    keyboard_height: int,
    scroll_y: int = 0,
    input_height: int = INPUT_HEIGHT_PX,
) -> bool:
    """Return True when the input's bottom edge is hidden behind the soft keyboard."""
    visible_bottom = viewport_height - keyboard_height
    input_bottom_in_viewport = input_top + input_height - scroll_y
    return input_bottom_in_viewport > visible_bottom
