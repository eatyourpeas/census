from __future__ import annotations

import math
import re
from typing import Tuple


HEX_RE = re.compile(r"^#(?P<r>[0-9a-fA-F]{2})(?P<g>[0-9a-fA-F]{2})(?P<b>[0-9a-fA-F]{2})$")


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _oklab_from_linear_rgb(r: float, g: float, b: float) -> Tuple[float, float, float]:
    # Reference implementation by Björn Ottosson
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l = l_ ** (1/3)
    m = m_ ** (1/3)
    s = s_ ** (1/3)

    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    b2 = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, a, b2


def hex_to_oklch(hex_color: str) -> str:
    """Convert #RRGGBB to an OKLCH triple string like "49.12% 0.3096 275.75".

    Returns an empty string if the input doesn't look like a hex color.
    """
    m = HEX_RE.match(hex_color.strip())
    if not m:
        return ""
    r = int(m.group("r"), 16) / 255.0
    g = int(m.group("g"), 16) / 255.0
    b = int(m.group("b"), 16) / 255.0

    rl = _srgb_to_linear(r)
    gl = _srgb_to_linear(g)
    bl = _srgb_to_linear(b)

    L, a, b2 = _oklab_from_linear_rgb(rl, gl, bl)
    C = math.sqrt(a * a + b2 * b2)
    h = math.degrees(math.atan2(b2, a)) % 360.0

    Lp = max(0.0, min(1.0, L)) * 100.0
    # Clamp chroma to a reasonable range to avoid out-of-gamut artifacts
    Cp = max(0.0, min(0.4, C))
    return f"{Lp:.2f}% {Cp:.4f} {h:.2f}"
