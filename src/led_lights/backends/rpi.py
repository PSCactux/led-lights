"""Raspberry Pi backend using rpi_ws281x (DMA-driven WS2812 output).

The library is imported lazily so the package installs and runs on any machine.
Needs root (or the right /dev/mem permissions) and a data pin such as GPIO18.
"""

from __future__ import annotations

from ..layout import serpentine
from ..power import Output


class RpiBackend:
    def __init__(self, leds: int, pin: int = 18, matrix_width: int | None = None,
                 zigzag: bool = False, freq_hz: int = 800_000, dma: int = 10):
        try:
            from rpi_ws281x import PixelStrip
        except ImportError:
            raise SystemExit(
                "The rpi backend needs rpi_ws281x (Raspberry Pi only):\n"
                "  uv sync --extra rpi   # or: pip install 'led-lights[rpi]'\n"
                "Use --backend sim to preview on this machine.") from None
        channel = 1 if pin in (13, 19, 41, 45, 53) else 0  # PWM1 pins use channel 1
        # Brightness 255 and no library gamma: OutputStage already did both.
        self.strip = PixelStrip(leds, pin, freq_hz, dma, False, 255, channel)
        self.strip.begin()
        self.width = matrix_width if zigzag else None

    def show(self, out: Output) -> None:
        frame = serpentine(out.hardware, self.width) if self.width else out.hardware
        for i, (r, g, b) in enumerate(frame):
            self.strip.setPixelColorRGB(i, r, g, b)
        self.strip.show()

    def close(self) -> None:
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColorRGB(i, 0, 0, 0)
        self.strip.show()
