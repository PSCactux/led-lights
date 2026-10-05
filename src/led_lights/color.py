"""Color helpers: the RGB type, HSV, blending, palettes, gamma tables and value noise."""

from __future__ import annotations

import math

RGB = tuple[int, int, int]
BLACK: RGB = (0, 0, 0)


def clamp8(x: float) -> int:
    """Clamp a number to an 8-bit channel value."""
    if x <= 0:
        return 0
    if x >= 255:
        return 255
    return int(x)


def rgb(r: float, g: float, b: float) -> RGB:
    return (clamp8(r), clamp8(g), clamp8(b))


def hsv(h: float, s: float = 1.0, v: float = 1.0) -> RGB:
    """HSV to RGB. `h` is in turns (0..1, wraps), `s` and `v` are 0..1."""
    h = (h % 1.0) * 6.0
    i = int(h) % 6
    f = h - int(h)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    u = v * (1.0 - s * (1.0 - f))
    r, g, b = ((v, u, p), (q, v, p), (p, v, u), (p, q, v), (u, p, v), (v, p, q))[i]
    return rgb(r * 255 + 0.5, g * 255 + 0.5, b * 255 + 0.5)


def scale(c: RGB, f: float) -> RGB:
    return rgb(c[0] * f, c[1] * f, c[2] * f)


def add(a: RGB, b: RGB) -> RGB:
    """Saturating add, like light adding up on the same pixel."""
    return rgb(a[0] + b[0], a[1] + b[1], a[2] + b[2])


def lerp(a: RGB, b: RGB, t: float) -> RGB:
    t = min(1.0, max(0.0, t))
    return rgb(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def smoothstep(e0: float, e1: float, x: float) -> float:
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# --- Palettes -----------------------------------------------------------------
# A palette is a list of evenly spaced color stops. Lookups interpolate between
# stops and wrap around, so animating the lookup position gives smooth cycles.

PALETTES: dict[str, list[RGB]] = {
    "rainbow": [hsv(i / 8) for i in range(8)],
    "party": [(85, 0, 171), (132, 0, 124), (181, 0, 75), (229, 0, 27), (232, 23, 0),
              (184, 71, 0), (171, 119, 0), (171, 171, 0), (171, 85, 0), (221, 34, 0),
              (242, 0, 14), (194, 0, 62), (143, 0, 113), (95, 0, 161), (47, 0, 208), (0, 7, 249)],
    "ocean": [(0, 0, 40), (0, 30, 110), (0, 110, 170), (60, 200, 220), (0, 70, 150), (0, 10, 70)],
    "lava": [(0, 0, 0), (110, 0, 0), (230, 30, 0), (255, 130, 0), (255, 220, 60), (150, 10, 0)],
    "forest": [(0, 40, 0), (20, 100, 10), (90, 160, 20), (30, 120, 60), (0, 70, 30), (60, 90, 0)],
    "aurora": [(0, 255, 120), (0, 200, 160), (30, 120, 255), (140, 40, 255), (0, 230, 90)],
}


def palette(stops: list[RGB] | str, x: float) -> RGB:
    """Sample a palette at position x (0..1, wraps)."""
    if isinstance(stops, str):
        stops = PALETTES[stops]
    n = len(stops)
    pos = (x % 1.0) * n
    i = int(pos) % n
    return lerp(stops[i], stops[(i + 1) % n], pos - int(pos))


def heat_color(heat: float) -> RGB:
    """Black body-ish ramp used by the fire effect (FastLED's HeatColor)."""
    t192 = int(min(255, max(0, heat)) * 191 / 255)
    ramp = (t192 & 0x3F) << 2
    if t192 & 0x80:
        return (255, 255, ramp)
    if t192 & 0x40:
        return (255, ramp, 0)
    return (ramp, 0, 0)


# --- Gamma --------------------------------------------------------------------
# LEDs are linear in PWM duty cycle but our eyes are not: 50% duty looks much
# brighter than "half". A gamma curve maps perceptual values to duty cycles.

DEFAULT_GAMMA = 2.6


def gamma_table(gamma: float = DEFAULT_GAMMA) -> list[int]:
    return [round(255 * (i / 255) ** gamma) for i in range(256)]


def apply_gamma(frame: list[RGB], table: list[int]) -> list[RGB]:
    return [(table[r], table[g], table[b]) for r, g, b in frame]


# --- Value noise ----------------------------------------------------------------
# Cheap smooth noise, good enough for organic motion (aurora, flicker).


def _hash(ix: int, iy: int, seed: int) -> float:
    n = (ix * 374761393 + iy * 668265263 + seed * 982451653) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def noise2(x: float, y: float, seed: int = 0) -> float:
    """2D value noise in 0..1."""
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed)
    b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed)
    d = _hash(ix + 1, iy + 1, seed)
    top = a + (b - a) * sx
    bottom = c + (d - c) * sx
    return top + (bottom - top) * sy


def fbm(x: float, y: float, octaves: int = 3, seed: int = 0) -> float:
    """Fractal sum of noise octaves, normalized to 0..1."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += noise2(x, y, seed + o) * amp
        norm += amp
        x, y, amp = x * 2.0, y * 2.0, amp * 0.5
    return total / norm
