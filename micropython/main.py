# led-lights for MicroPython (ESP32, Raspberry Pi Pico, ...).
#
# Self-contained port of a few effects using the built-in `neopixel` module.
# Copy this file to the board as main.py (e.g. `mpremote cp main.py :main.py`)
# and adjust the settings below. It cycles through the effects forever.
#
# It also runs under desktop CPython (python3 main.py) with a fake NeoPixel
# that prints the strip in the terminal, which is how it is tested.

import math
import random
import time

# --- Settings -----------------------------------------------------------------
PIN = 5             # data pin: e.g. GPIO5 on ESP32, GP0 on a Pico
NUM_LEDS = 60
BRIGHTNESS = 0.4    # 0..1 (perceptual)
MAX_MA = 1000       # current budget of your 5 V supply, in mA
FPS = 50
SECONDS_PER_EFFECT = 20
GAMMA = 2.6

try:
    import machine
    import neopixel
    strip = neopixel.NeoPixel(machine.Pin(PIN), NUM_LEDS)
except ImportError:  # desktop fallback for testing
    class _FakeStrip:
        def __init__(self, n):
            self.buf = [(0, 0, 0)] * n
            self.verbose = False

        def __setitem__(self, i, c):
            self.buf[i] = c

        def __getitem__(self, i):
            return self.buf[i]

        def __len__(self):
            return len(self.buf)

        def write(self):
            if self.verbose:
                # Show the gamma-corrected values brightened back up for screens.
                px = ["\x1b[38;2;%d;%d;%dm█" % tuple(int(255 * (c / 255) ** (1 / GAMMA)) for c in p)
                      for p in self.buf]
                print("\r" + "".join(px) + "\x1b[0m", end="")

    strip = _FakeStrip(NUM_LEDS)

try:
    ticks_ms, ticks_diff = time.ticks_ms, time.ticks_diff
except AttributeError:  # CPython
    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

GAMMA_TABLE = bytearray(int(255 * (i / 255) ** GAMMA + 0.5) for i in range(256))


def hsv(h, s=1.0, v=1.0):
    h = (h % 1.0) * 6.0
    i = int(h) % 6
    f = h - int(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i]
    return (int(r * 255), int(g * 255), int(b * 255))


def scale(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


# --- Effects: each takes (t seconds, n LEDs) and returns a list of RGB tuples ---

def rainbow(t, n):
    return [hsv(i / n - t * 0.25) for i in range(n)]


def comet(t, n):
    tail = max(3, n // 5)
    period = max(1.0, n / 40)
    phase = (t / period) % 2.0
    fwd = phase < 1.0
    pos = (phase if fwd else 2.0 - phase) * (n - 1)
    color = hsv(t * 0.05)
    out = []
    for i in range(n):
        d = pos - i if fwd else i - pos
        out.append(scale(color, (1 - d / tail) ** 2) if 0 <= d < tail else (0, 0, 0))
    return out


_heat = [0] * NUM_LEDS


def fire(t, n):
    for i in range(n):
        _heat[i] = max(0, _heat[i] - random.randint(0, 550 // n + 2))
    for k in range(n - 1, 1, -1):
        _heat[k] = (_heat[k - 1] + 2 * _heat[k - 2]) // 3
    if random.randint(0, 255) < 120:
        y = random.randint(0, min(6, n - 1))
        _heat[y] = min(255, _heat[y] + random.randint(160, 255))
    out = []
    for h in _heat[:n]:
        t192 = h * 191 // 255
        ramp = (t192 & 0x3F) << 2
        out.append((255, 255, ramp) if t192 & 0x80 else (255, ramp, 0) if t192 & 0x40 else (ramp, 0, 0))
    return out


_stars = [(1.5 + 3 * random.random(), random.random()) for _ in range(NUM_LEDS)]


def twinkle(t, n):
    out = []
    for period, phase in _stars[:n]:
        v = math.sin(2 * math.pi * (t / period + phase))
        b = max(0.0, (v - 0.55) / 0.45) ** 2
        out.append((int(255 * b), int(220 * b), int(6 + 160 * b)))
    return out


def breathing(t, n):
    b = (math.exp(math.sin(t * 2 * math.pi / 4.0)) - 1 / math.e) / (math.e - 1 / math.e)
    return [hsv(0.55, 0.8, 0.05 + 0.95 * b)] * n


def theater_chase(t, n):
    step = int(t * 12)
    return [hsv(i / n + t * 0.1) if (i + step) % 3 == 0 else (0, 0, 0) for i in range(n)]


EFFECTS = [rainbow, comet, fire, twinkle, breathing, theater_chase]


# --- Output: brightness -> gamma -> current limit ---------------------------------

def show(frame):
    b = BRIGHTNESS
    out = [(GAMMA_TABLE[int(r * b)], GAMMA_TABLE[int(g * b)], GAMMA_TABLE[int(bl * b)])
           for r, g, bl in frame]
    # ~20 mA per channel at full duty, ~1 mA idle per LED (WS2812B).
    idle = len(out)
    ma = idle + sum(r + g + bl for r, g, bl in out) * 20 / 255
    if ma > MAX_MA:
        f = max(0.0, (MAX_MA - idle) / (ma - idle))
        out = [scale(c, f) for c in out]
    for i, c in enumerate(out):
        strip[i] = c
    strip.write()
    return ma


def run(max_frames=None):
    start = ticks_ms()
    frame_ms = 1000 // FPS
    frames = 0
    while max_frames is None or frames < max_frames:
        t0 = ticks_ms()
        t = ticks_diff(t0, start) / 1000
        effect = EFFECTS[int(t // SECONDS_PER_EFFECT) % len(EFFECTS)]
        show(effect(t, NUM_LEDS))
        frames += 1
        wait = frame_ms - ticks_diff(ticks_ms(), t0)
        if wait > 0:
            time.sleep(wait / 1000)


if __name__ == "__main__":
    if hasattr(strip, "verbose"):
        strip.verbose = True
        SECONDS_PER_EFFECT = 4
    try:
        run()
    except KeyboardInterrupt:
        for i in range(NUM_LEDS):
            strip[i] = (0, 0, 0)
        strip.write()
