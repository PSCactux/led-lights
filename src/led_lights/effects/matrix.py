"""2D effects for LED matrices (row-major, pixel 0 is the top-left corner)."""

from __future__ import annotations

import math

from ..color import BLACK, hsv, palette, rgb, scale
from .base import Effect


class MatrixEffect(Effect):
    matrix = True
    default_leds = 256


class Plasma2D(MatrixEffect):
    name = "plasma2d"
    description = "Old-school demoscene plasma"

    def draw(self, t, dt):
        w, h = self.w, self.h
        k = 16 / max(w, h)  # keep the same look on smaller panels
        out = []
        for y in range(h):
            for x in range(w):
                X, Y = x * k, y * k
                cx, cy = X - 8 + 4 * math.sin(t * 0.5), Y - 8 + 4 * math.cos(t * 0.3)
                v = (math.sin(X * 0.4 + t) + math.sin((Y * 0.3 - t) * 1.3)
                     + math.sin((X + Y) * 0.25 + t * 0.7) + math.sin(math.hypot(cx, cy) * 0.6 - t * 1.5))
                out.append(palette("rainbow", (v + 4) / 8 + t * 0.03))
        return out


class MatrixRain(MatrixEffect):
    name = "matrix_rain"
    description = "Falling green code rain with bright heads"
    gif_seconds = 5.0

    def reset(self):
        self.buf = [0.0] * (self.w * self.h)  # trail intensity per pixel
        self.drops = [self.new_drop(initial=True) for _ in range(self.w)]

    def new_drop(self, initial: bool = False) -> list[float]:
        start = -self.rng.uniform(0, self.h * (1.5 if initial else 0.8))
        return [start, self.rng.uniform(6.0, 14.0)]  # [y, rows per second]

    def draw(self, t, dt):
        w, h = self.w, self.h
        fade = 0.02 ** dt  # trails lose 98% per second (~6 pixel tail)
        self.buf = [v * fade for v in self.buf]
        heads = set()
        for x, drop in enumerate(self.drops):
            prev = int(drop[0])
            drop[0] += drop[1] * dt
            for y in range(max(0, prev), min(h, int(drop[0]) + 1)):
                self.buf[y * w + x] = 1.0
            if 0 <= int(drop[0]) < h:
                heads.add(int(drop[0]) * w + x)
            if drop[0] >= h + 2:
                self.drops[x] = self.new_drop()
        out = []
        for i, v in enumerate(self.buf):
            if i in heads:
                out.append((180, 255, 180))
            else:
                out.append(rgb(0, 255 * v, 40 * v * v))
        return out


class Life(MatrixEffect):
    name = "life"
    description = "Conway's Game of Life on a torus, colored by cell age; reseeds when stale"
    generation_seconds = 0.15
    gif_seconds = 6.0

    def reset(self):
        self.acc = 0.0
        self.seed_board()

    def seed_board(self):
        self.age = [1 if self.rng.random() < 0.35 else 0 for _ in range(self.w * self.h)]
        self.history: list[int] = []
        self.generations = 0

    def step(self):
        w, h, age = self.w, self.h, self.age
        nxt = [0] * (w * h)
        for y in range(h):
            for x in range(w):
                alive = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if (dx or dy) and age[((y + dy) % h) * w + (x + dx) % w]:
                            alive += 1
                i = y * w + x
                if age[i] and alive in (2, 3):
                    nxt[i] = age[i] + 1
                elif not age[i] and alive == 3:
                    nxt[i] = 1
        self.age = nxt
        self.generations += 1
        # Reseed when the board dies, loops (period <= 4) or runs too long.
        state = hash(tuple(a > 0 for a in nxt))
        if not any(nxt) or state in self.history or self.generations > 300:
            self.seed_board()
        else:
            self.history = (self.history + [state])[-4:]

    def draw(self, t, dt):
        self.acc += dt
        while self.acc >= self.generation_seconds:
            self.acc -= self.generation_seconds
            self.step()
        return [hsv(0.35 + min(a, 30) / 40, 0.9, 1.0) if a else BLACK for a in self.age]


class Spiral(MatrixEffect):
    name = "spiral"
    description = "Rotating three-armed rainbow spiral"

    def draw(self, t, dt):
        w, h = self.w, self.h
        cx, cy = (w - 1) / 2, (h - 1) / 2
        k = 16 / max(w, h)
        out = []
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                a = math.atan2(dy, dx)
                r = math.hypot(dx, dy) * k
                b = 0.5 + 0.5 * math.sin(3 * a + r * 0.7 - t * 4)
                out.append(scale(hsv(a / (2 * math.pi) + r * 0.03 + t * 0.1), b * b))
        return out


MATRIX_EFFECTS = [Plasma2D, MatrixRain, Life, Spiral]
