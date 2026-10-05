"""Brightness, current estimation and current limiting.

A WS2812B pixel draws roughly 20 mA per color channel at full duty (60 mA for
full white) plus about 1 mA quiescent. The estimate is linear in duty cycle,
so it must be computed on the gamma-corrected values actually sent to the strip.
"""

from __future__ import annotations

from dataclasses import dataclass

from .color import DEFAULT_GAMMA, RGB, apply_gamma, gamma_table, scale

MA_PER_CHANNEL = 20.0
MA_IDLE_PER_LED = 1.0


def apply_brightness(frame: list[RGB], brightness: float) -> list[RGB]:
    brightness = min(1.0, max(0.0, brightness))
    if brightness == 1.0:
        return list(frame)
    return [scale(c, brightness) for c in frame]


def estimate_ma(frame: list[RGB], ma_per_channel: float = MA_PER_CHANNEL,
                idle_ma: float = MA_IDLE_PER_LED) -> float:
    """Estimated strip current in mA for a frame of raw duty-cycle values."""
    total = sum(r + g + b for r, g, b in frame)
    return len(frame) * idle_ma + total / 255.0 * ma_per_channel


def limit_scale(frame: list[RGB], max_ma: float | None, ma_per_channel: float = MA_PER_CHANNEL,
                idle_ma: float = MA_IDLE_PER_LED) -> float:
    """Factor (0..1) to multiply a frame by so it stays under `max_ma`."""
    if not max_ma:
        return 1.0
    idle = len(frame) * idle_ma
    est = estimate_ma(frame, ma_per_channel, idle_ma)
    if est <= max_ma:
        return 1.0
    # The quiescent current cannot be scaled away, only the color part.
    return max(0.0, (max_ma - idle) / (est - idle))


def limit_current(frame: list[RGB], max_ma: float | None) -> tuple[list[RGB], float]:
    """Scale a frame down if it would exceed `max_ma`. Returns (frame, factor)."""
    f = limit_scale(frame, max_ma)
    if f >= 1.0:
        return list(frame), 1.0
    return [(int(r * f), int(g * f), int(b * f)) for r, g, b in frame], f


@dataclass
class Output:
    hardware: list[RGB]  # gamma-corrected, brightness- and current-limited: send this to LEDs
    display: list[RGB]  # what a screen should show (screens already apply their own gamma)
    ma: float  # estimated current of `hardware`
    limit: float  # current limiter factor applied (1.0 = not limiting)


class OutputStage:
    """Turns an effect frame into hardware values: brightness -> gamma -> current limit."""

    def __init__(self, brightness: float = 0.6, max_ma: float | None = 2000.0,
                 gamma: float = DEFAULT_GAMMA):
        self.brightness = brightness
        self.max_ma = max_ma
        self.gamma = gamma
        self.table = gamma_table(gamma)

    def process(self, frame: list[RGB]) -> Output:
        # Brightness is applied before gamma so 0.5 looks like "half as bright".
        dimmed = apply_brightness(frame, self.brightness)
        hardware, f = limit_current(apply_gamma(dimmed, self.table), self.max_ma)
        # Mirror the limiter on the display copy in perceptual space.
        display = dimmed if f >= 1.0 else [scale(c, f ** (1 / self.gamma)) for c in dimmed]
        return Output(hardware, display, estimate_ma(hardware), f)
