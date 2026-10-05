"""Simulator backends: a live 24-bit ANSI terminal preview and GIF / PNG rendering."""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from ..color import RGB
from ..effects import Effect
from ..power import Output, OutputStage


class TerminalBackend:
    """Draws the strip (or matrix) in the terminal with true-color escape codes."""

    def __init__(self, width: int | None = None, stream=sys.stdout):
        self.width = width  # matrix width; None for a strip
        self.out = stream
        self.frames = 0
        self.t0 = time.perf_counter()
        self.out.write("\x1b[2J\x1b[?25l")  # clear screen, hide cursor

    def lines(self, frame: list[RGB]) -> list[str]:
        if self.width:  # matrix: two pixel rows per text row using the upper half block
            w = self.width
            rows = [frame[i:i + w] for i in range(0, len(frame), w)]
            lines = []
            for top, bottom in zip(rows[::2], rows[1::2] + [[]]):
                cells = []
                for x, (r, g, b) in enumerate(top):
                    br, bg, bb = bottom[x] if x < len(bottom) else (0, 0, 0)
                    cells.append(f"\x1b[38;2;{r};{g};{b}m\x1b[48;2;{br};{bg};{bb}m▀▀")
                lines.append("".join(cells) + "\x1b[0m")
            return lines
        cols = max(10, shutil.get_terminal_size((80, 24)).columns - 1)
        return ["".join(f"\x1b[38;2;{r};{g};{b}m█" for r, g, b in frame[i:i + cols]) + "\x1b[0m"
                for i in range(0, len(frame), cols)]

    def show(self, out: Output) -> None:
        self.frames += 1
        fps = self.frames / max(1e-6, time.perf_counter() - self.t0)
        status = f"{len(out.display)} LEDs  {fps:5.1f} fps  ~{out.ma:6.0f} mA"
        if out.limit < 1.0:
            status += f"  (current limited to {out.limit:.0%})"
        self.out.write("\x1b[H" + "\n".join(self.lines(out.display)) + f"\n\x1b[K{status}  Ctrl+C to quit\n")
        self.out.flush()

    def close(self) -> None:
        self.out.write("\x1b[0m\x1b[?25h\n")
        self.out.flush()


# --- Image rendering ------------------------------------------------------------

STRIP_COLUMNS = 60  # long strips wrap into rows of this many LEDs in images
BACKGROUND = (12, 12, 16)


def _grid(n: int, width: int | None) -> tuple[int, int]:
    cols = width or min(n, STRIP_COLUMNS)
    return cols, -(-n // cols)


def draw_frame(frame: list[RGB], width: int | None = None, cell: int = 12):
    """Render one frame as LEDs with a soft glow. Returns a PIL image."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    cols, rows = _grid(len(frame), width)
    pad = cell // 2
    size = (cols * cell + 2 * pad, rows * cell + 2 * pad)
    leds = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(leds)
    body = Image.new("RGB", size, BACKGROUND)
    db = ImageDraw.Draw(body)
    r = cell * 0.36
    for i, c in enumerate(frame):
        x = pad + (i % cols) * cell + cell / 2
        y = pad + (i // cols) * cell + cell / 2
        db.ellipse((x - r, y - r, x + r, y + r), fill=(28, 28, 34))  # unlit LED package
        if c != (0, 0, 0):
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    glow = leds.filter(ImageFilter.GaussianBlur(cell * 0.45))
    return ImageChops.add(ImageChops.add(body, leds), glow)


def render_frames(effect: Effect, leds: int, seconds: float, fps: float,
                  stage: OutputStage | None = None) -> list[list[RGB]]:
    stage = stage or OutputStage(brightness=1.0, max_ma=None)
    return [stage.process(effect.render(i / fps, leds)).display for i in range(int(seconds * fps))]


def save_gif(frames: list[list[RGB]], path: Path, fps: float, width: int | None = None,
             cell: int = 12) -> Path:
    from PIL import Image

    images = [draw_frame(f, width, cell) for f in frames]
    # One shared palette for every frame (built from a sample of frames) keeps
    # colors stable and lets the GIF encoder store only what changed per frame.
    sample = images[:: max(1, len(images) // 12)]
    sheet = Image.new("RGB", (images[0].width, images[0].height * len(sample)))
    for i, im in enumerate(sample):
        sheet.paste(im, (0, i * im.height))
    shared = sheet.quantize(255, method=Image.Quantize.MEDIANCUT)
    images = [im.quantize(palette=shared, dither=Image.Dither.NONE) for im in images]
    path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(path, save_all=True, append_images=images[1:], duration=round(1000 / fps),
                   loop=0, optimize=True, disposal=1)
    return path


def save_timeline(frames: list[list[RGB]], path: Path, cell: int = 4) -> Path:
    """Space-time PNG: one row per frame, one column per LED (time flows down)."""
    from PIL import Image

    img = Image.new("RGB", (len(frames[0]), len(frames)))
    img.putdata([c for f in frames for c in f])
    img = img.resize((img.width * cell, img.height * cell), Image.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
