"""Run the MicroPython port under CPython with its fake NeoPixel fallback."""

import importlib.util
from pathlib import Path

import pytest

MAIN = Path(__file__).parent.parent / "micropython" / "main.py"


@pytest.fixture(scope="module")
def mp():
    spec = importlib.util.spec_from_file_location("mp_main", MAIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_effect_renders(mp):
    for effect in mp.EFFECTS:
        for i in range(120):
            frame = effect(i / 50, mp.NUM_LEDS)
            assert len(frame) == mp.NUM_LEDS
            assert all(len(c) == 3 and all(0 <= v <= 255 for v in c) for c in frame)


def test_show_respects_current_budget(mp, monkeypatch):
    monkeypatch.setattr(mp, "BRIGHTNESS", 1.0)
    ma = mp.show([(255, 255, 255)] * mp.NUM_LEDS)
    assert ma > mp.MAX_MA  # raw frame was over budget...
    written = mp.strip.buf
    est = mp.NUM_LEDS + sum(sum(c) for c in written) * 20 / 255
    assert est <= mp.MAX_MA  # ...but what reached the strip is not


def test_run_loop(mp):
    mp.run(max_frames=5)
