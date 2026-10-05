"""The Effect interface shared by every animation."""

from __future__ import annotations

import math
import random

from ..color import RGB


class Effect:
    """An animation. Call `render(t, leds)` once per frame.

    `t` is the time in seconds since the animation started, `leds` the number of
    pixels. It returns exactly `leds` RGB tuples. Effects may keep state between
    calls (fire, physics); that state is reset when the LED count changes.

    Matrix effects lay pixels out row-major on a `width` x `height` grid. The
    width defaults to the square root of `leds` (16 for 256 LEDs).
    """

    name = ""
    description = ""
    matrix = False
    default_leds = 60
    gif_seconds = 4.0

    def __init__(self, seed: int | None = 1234, width: int | None = None):
        self.seed = seed
        self.width = width
        self.rng = random.Random(seed)
        self.n = self.w = self.h = 0
        self._last_t: float | None = None

    def render(self, t: float, leds: int) -> list[RGB]:
        if leds <= 0:
            return []
        if leds != self.n:
            self.n = leds
            self.w = min(leds, self.width or max(1, math.isqrt(leds))) if self.matrix else leds
            self.h = -(-leds // self.w) if self.matrix else 1
            self.rng = random.Random(self.seed)
            self._last_t = t
            self.reset()
        # Frame delta for stateful effects, clamped so a stall does not explode physics.
        dt = min(0.1, max(0.0, t - self._last_t))
        self._last_t = t
        frame = self.draw(t, dt)
        return frame[:leds]

    def reset(self) -> None:
        """Called when the LED count changes (and before the first frame)."""

    def draw(self, t: float, dt: float) -> list[RGB]:
        raise NotImplementedError
