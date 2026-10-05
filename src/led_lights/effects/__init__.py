"""Effect registry."""

from __future__ import annotations

from .base import Effect
from .matrix import MATRIX_EFFECTS
from .strip import STRIP_EFFECTS

EFFECTS: dict[str, type[Effect]] = {cls.name: cls for cls in STRIP_EFFECTS + MATRIX_EFFECTS}


def get_effect(name: str, **kwargs) -> Effect:
    try:
        return EFFECTS[name](**kwargs)
    except KeyError:
        raise SystemExit(f"Unknown effect '{name}'. Try: {', '.join(EFFECTS)}") from None


__all__ = ["EFFECTS", "Effect", "get_effect"]
