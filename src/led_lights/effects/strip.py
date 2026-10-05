"""1D effects for LED strips. Pixel 0 is the start of the strip (the "floor")."""

from __future__ import annotations

import math

from ..color import (BLACK, RGB, add, fbm, heat_color, hsv, lerp, palette, rgb, scale,
                     smoothstep, _hash)
from .base import Effect


class Rainbow(Effect):
    name = "rainbow"
    description = "Classic scrolling rainbow across the whole strip"

    def draw(self, t, dt):
        n = self.n
        return [hsv(i / n - t * 0.25) for i in range(n)]


class Comet(Effect):
    name = "comet"
    description = "A bright head bouncing back and forth with a fading tail"

    def draw(self, t, dt):
        n = self.n
        tail = max(3.0, n / 5)
        period = max(1.0, n / 40)  # seconds per pass, ~40 LEDs/s
        phase = (t / period) % 2.0
        forward = phase < 1.0
        pos = (phase if forward else 2.0 - phase) * (n - 1)
        color = hsv(t * 0.05)
        out = []
        for i in range(n):
            d = pos - i if forward else i - pos  # distance behind the head
            if -1.0 < d < 0.0:
                b = 1.0 + d  # anti-aliased leading edge
            elif 0.0 <= d < tail:
                b = (1.0 - d / tail) ** 2
            else:
                b = 0.0
            c = scale(color, b)
            if 0.0 <= d < 1.0:  # white-hot head
                c = add(c, scale((255, 255, 255), 0.6 * (1.0 - d)))
            out.append(c)
        return out


class Fire(Effect):
    name = "fire"
    description = "Heat-diffusion fire (Fire2012): sparks at the base rise and cool"
    cooling, sparking, step_hz = 55, 120, 60.0

    def reset(self):
        self.heat = [0.0] * self.n
        self.acc = 0.0

    def step(self):
        n, heat, rng = self.n, self.heat, self.rng
        for i in range(n):  # 1. every cell cools a little
            heat[i] = max(0.0, heat[i] - rng.randint(0, (self.cooling * 10) // n + 2))
        for k in range(n - 1, 1, -1):  # 2. heat drifts up and diffuses
            heat[k] = (heat[k - 1] + 2 * heat[k - 2]) / 3
        if rng.randint(0, 255) < self.sparking:  # 3. random sparks near the bottom
            y = rng.randint(0, min(6, n - 1))
            heat[y] = min(255.0, heat[y] + rng.randint(160, 255))

    def draw(self, t, dt):
        # The simulation runs at a fixed rate so it looks the same at any fps.
        self.acc += dt
        while self.acc >= 1 / self.step_hz:
            self.acc -= 1 / self.step_hz
            self.step()
        return [heat_color(h) for h in self.heat]


class Twinkle(Effect):
    name = "twinkle"
    description = "Stars fading in and out at random over a night-blue sky"
    colors = [(255, 220, 160), (160, 200, 255), (255, 255, 255), (255, 180, 80)]

    def draw(self, t, dt):
        out = []
        for i in range(self.n):
            period = 1.5 + 3.0 * _hash(i, 1, 7)
            phase = _hash(i, 2, 7)
            v = math.sin(2 * math.pi * (t / period + phase))
            b = max(0.0, (v - 0.55) / 0.45) ** 2
            star = self.colors[int(_hash(i, 3, 7) * len(self.colors)) % len(self.colors)]
            out.append(add((0, 0, 6), scale(star, b)))
        return out


class Breathing(Effect):
    name = "breathing"
    description = "Slow 'sleep LED' breathing with a drifting hue"

    def draw(self, t, dt):
        # exp(sin) gives the quick inhale / long exhale of a real breathing light.
        b = (math.exp(math.sin(t * 2 * math.pi / 4.0)) - 1 / math.e) / (math.e - 1 / math.e)
        c = hsv(0.55 + 0.15 * math.sin(t * 0.2), 0.8, 0.05 + 0.95 * b)
        return [c] * self.n


class ColorWipe(Effect):
    name = "color_wipe"
    description = "Fill the strip one LED at a time, then wipe with the next color"
    colors = [(255, 0, 40), (255, 140, 0), (0, 220, 80), (0, 120, 255), (160, 0, 255)]
    gif_seconds = 6.0

    def draw(self, t, dt):
        n = self.n
        dur = max(0.5, n / 50)  # ~50 LEDs/s
        k = int(t // dur)
        progress = (t % dur) / dur * n
        new, old = self.colors[k % len(self.colors)], self.colors[(k - 1) % len(self.colors)]
        return [lerp(old, new, progress - i) for i in range(n)]


class TheaterChase(Effect):
    name = "theater_chase"
    description = "Marquee lights: every third LED on, marching along, rainbow tinted"

    def draw(self, t, dt):
        step = int(t * 12)
        return [hsv(i / self.n + t * 0.1) if (i + step) % 3 == 0 else BLACK for i in range(self.n)]


class Plasma(Effect):
    name = "plasma"
    description = "Sum of sine waves mapped through a palette"

    def draw(self, t, dt):
        out = []
        for i in range(self.n):
            v = (math.sin(i * 0.15 + t * 1.1) + math.sin(i * 0.07 - t * 1.7)
                 + math.sin(i * 0.23 + math.sin(t * 0.5) * 3))
            out.append(palette("party", (v + 3) / 6 + t * 0.05))
        return out


class Aurora(Effect):
    name = "aurora"
    description = "Northern lights: slow fractal noise curtains in green and violet"
    gif_seconds = 6.0

    def draw(self, t, dt):
        n = self.n
        out = []
        for i in range(n):
            x = i / max(1, n) * 5.0
            v = fbm(x + t * 0.12, t * 0.25, 3, seed=11)
            b = smoothstep(0.35, 0.8, v)
            c = palette("aurora", fbm(x * 0.4, t * 0.08 + 50, 2, seed=3) * 1.5)
            out.append(add((0, 2, 4), scale(c, b)))
        return out


class MeteorRain(Effect):
    name = "meteor_rain"
    description = "Meteors streak along leaving trails that decay at random"
    step_hz = 60.0

    def reset(self):
        self.buf = [[0.0, 0.0, 0.0] for _ in range(self.n)]
        self.pos = 0.0
        self.color = hsv(self.rng.random(), 0.3, 1.0)
        self.acc = 0.0

    def draw(self, t, dt):
        n = self.n
        speed = max(30.0, n * 0.8)  # LEDs per second
        self.acc += dt
        while self.acc >= 1 / self.step_hz:
            self.acc -= 1 / self.step_hz
            for px in self.buf:  # random decay keeps the trail sparkly
                if self.rng.random() < 0.5:
                    for ch in range(3):
                        px[ch] *= 0.8
            self.pos += speed / self.step_hz
            if self.pos > n * 1.6:
                self.pos = 0.0
                self.color = hsv(self.rng.random(), 0.3, 1.0)
            for j in range(4):  # meteor head, 4 pixels
                k = int(self.pos) - j
                if 0 <= k < n:
                    self.buf[k] = [float(c) for c in self.color]
        return [rgb(*px) for px in self.buf]


class BouncingBalls(Effect):
    name = "bouncing_balls"
    description = "Balls bouncing under gravity with energy loss; pixel 0 is the floor"
    colors = [(255, 40, 0), (0, 160, 255), (120, 255, 0), (255, 0, 200)]
    gravity = 9.81
    gif_seconds = 6.0

    def reset(self):
        k = 3 if self.n < 30 else 4
        self.balls = [[0.0, self.launch(), 0.92 - 0.04 * i] for i in range(k)]  # [h, v, restitution]

    def launch(self) -> float:
        # Velocity needed to reach a height between 0.6 and 1.0 (strip length = 1 m).
        return math.sqrt(2 * self.gravity * self.rng.uniform(0.6, 1.0))

    def draw(self, t, dt):
        for _ in range(4):  # substeps for stable bounces
            h_dt = dt / 4
            for ball in self.balls:
                ball[1] -= self.gravity * h_dt
                ball[0] += ball[1] * h_dt
                if ball[0] < 0:
                    ball[0] = 0.0
                    ball[1] = -ball[1] * ball[2]
                    if ball[1] < 1.2:
                        ball[1] = self.launch()
        out = [BLACK] * self.n
        for i, (h, _, _) in enumerate(self.balls):
            p = min(1.0, h) * (self.n - 1)
            k = int(p)
            frac = p - k
            c = self.colors[i % len(self.colors)]
            out[k] = add(out[k], scale(c, 1 - frac))
            if k + 1 < self.n:
                out[k + 1] = add(out[k + 1], scale(c, frac))
        return out


class Heartbeat(Effect):
    name = "heartbeat"
    description = "Lub-dub pulse at 72 bpm spreading out from the middle"

    @staticmethod
    def envelope(t: float) -> float:
        p = t % (60 / 72)
        lub = math.exp(-((p - 0.05) / 0.045) ** 2)
        dub = 0.6 * math.exp(-((p - 0.28) / 0.06) ** 2)
        return lub + dub

    def draw(self, t, dt):
        n = self.n
        mid = (n - 1) / 2
        out = []
        for i in range(n):
            d = abs(i - mid) / max(1.0, mid)
            b = self.envelope(t - d * 0.25) * (1 - 0.6 * d)
            out.append(rgb(255 * b, 10 * b, 25 * b))
        return out


STRIP_EFFECTS = [Rainbow, Comet, Fire, Twinkle, Breathing, ColorWipe, TheaterChase, Plasma,
                 Aurora, MeteorRain, BouncingBalls, Heartbeat]
