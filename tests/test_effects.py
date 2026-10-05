import pytest

from led_lights.effects import EFFECTS, get_effect

LED_COUNTS = [1, 7, 60, 144, 256]
TIMES = [0.0, 0.016, 0.5, 1.0, 3.7, 10.0, 100.0]


def valid(frame, n):
    assert len(frame) == n
    for px in frame:
        assert isinstance(px, tuple) and len(px) == 3
        assert all(isinstance(c, int) and 0 <= c <= 255 for c in px)


@pytest.mark.parametrize("name", list(EFFECTS))
@pytest.mark.parametrize("leds", LED_COUNTS)
def test_effect_returns_valid_frames(name, leds):
    effect = get_effect(name)
    for t in TIMES:
        valid(effect.render(t, leds), leds)


@pytest.mark.parametrize("name", list(EFFECTS))
def test_effect_survives_a_long_run_and_resize(name):
    effect = get_effect(name)
    for i in range(600):  # 10 s at 60 fps exercises the stateful effects
        valid(effect.render(i / 60, 60), 60)
    valid(effect.render(10.0, 30), 30)  # changing LED count resets state
    assert effect.render(10.0, 0) == []


@pytest.mark.parametrize("name", list(EFFECTS))
def test_effect_is_not_blank(name):
    effect = get_effect(name)
    leds = effect.default_leds
    frames = [effect.render(i / 30, leds) for i in range(150)]
    assert any(any(sum(px) > 0 for px in f) for f in frames)


@pytest.mark.parametrize("name", list(EFFECTS))
def test_same_seed_is_deterministic(name):
    a, b = get_effect(name, seed=7), get_effect(name, seed=7)
    for i in range(60):
        assert a.render(i / 30, 64) == b.render(i / 30, 64)


def test_matrix_width_override():
    effect = get_effect("spiral", width=8)
    valid(effect.render(0.5, 32), 32)
    assert (effect.w, effect.h) == (8, 4)
