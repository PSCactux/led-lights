"""Mapping between logical pixel order and physical wiring."""

from __future__ import annotations

from .color import RGB


def serpentine(frame: list[RGB], width: int) -> list[RGB]:
    """Reorder a row-major frame for a zig-zag wired matrix (odd rows reversed).

    Most 16x16 WS2812 panels are wired this way: row 0 left-to-right, row 1
    right-to-left, and so on.
    """
    out: list[RGB] = []
    for y in range(0, len(frame), width):
        row = frame[y:y + width]
        out.extend(reversed(row) if (y // width) % 2 else row)
    return out
