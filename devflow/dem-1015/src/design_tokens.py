"""Design tokens and WCAG contrast utilities for the login page.

The subjective "tech feel" requirement is expressed as quantifiable tokens so the
visual checklist (AC-DEM-1015-011) and accessibility contrast checks
(AC-DEM-1015-013) can be verified in code instead of by eye.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .motion import is_ease_out, is_valid_motion_duration

# Dark base luminance must stay below 30% (AC-DEM-1015-011 item 1).
DARK_BASE_MAX_LUMINANCE = 0.30

# WCAG 2.1 AA contrast thresholds (AC-DEM-1015-013).
TEXT_CONTRAST_MIN = 4.5
LARGE_ICON_CONTRAST_MIN = 3.0


def _parse_hex(color: str) -> Tuple[float, float, float]:
    """Parse a ``#RRGGBB`` (or ``#RGB``) hex color into sRGB channels in [0, 1]."""
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {color!r}")
    return (
        int(value[0:2], 16) / 255.0,
        int(value[2:4], 16) / 255.0,
        int(value[4:6], 16) / 255.0,
    )


def _linearize(channel: float) -> float:
    """Convert one sRGB channel to linear light per the WCAG formula."""
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    """Return the WCAG relative luminance of a hex color (range 0..1)."""
    r, g, b = _parse_hex(color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio between two hex colors (range 1..21)."""
    l1 = relative_luminance(foreground)
    l2 = relative_luminance(background)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


@dataclass(frozen=True)
class DesignTokens:
    """Design tokens that express the "tech feel" spec.

    One primary color (cyan glow), one secondary color (violet accent), and a
    neutral dark scale. All visual knobs live here so rebranding only changes
    variables, not components.
    """

    primary: str = "#00E5FF"
    secondary: str = "#7C4DFF"
    background: str = "#0A0E1A"
    surface: str = "#12182B"
    text_primary: str = "#E6F1FF"
    text_secondary: str = "#8A97B5"
    error: str = "#FF5470"
    focus_ring: str = "#00E5FF"
    border_glow: str = "#00E5FF"
    radius_px: int = 12


DEFAULT_TOKENS = DesignTokens()


@dataclass(frozen=True)
class VisualSpec:
    """The six-point tech-feel checklist from AC-DEM-1015-011."""

    background_color: str = DEFAULT_TOKENS.background
    has_dynamic_background: bool = True
    has_glow_or_glass: bool = True
    button_has_three_states: bool = True
    motion_duration_ms: int = 250
    easing: str = "ease-out"
    primary_color_count: int = 1
    secondary_color_count: int = 1


def validate_visual_checklist(spec: VisualSpec) -> List[str]:
    """Return a list of failed checklist items (empty list means all pass)."""
    failures: List[str] = []
    if relative_luminance(spec.background_color) >= DARK_BASE_MAX_LUMINANCE:
        failures.append("dark_base")
    if not spec.has_dynamic_background:
        failures.append("dynamic_background")
    if not spec.has_glow_or_glass:
        failures.append("glow_or_glass")
    if not spec.button_has_three_states:
        failures.append("button_states")
    if not is_valid_motion_duration(spec.motion_duration_ms):
        failures.append("motion_duration")
    if not is_ease_out(spec.easing):
        failures.append("easing")
    if spec.primary_color_count > 1 or spec.secondary_color_count > 1:
        failures.append("color_palette")
    return failures
