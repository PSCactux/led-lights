from led_lights.color import apply_gamma, gamma_table, hsv, palette
from led_lights.layout import serpentine
from led_lights.power import OutputStage, apply_brightness, estimate_ma, limit_current

WHITE = (255, 255, 255)


def test_gamma_table_endpoints_and_monotonic():
    table = gamma_table(2.6)
    assert len(table) == 256 and table[0] == 0 and table[255] == 255
    assert all(a <= b for a, b in zip(table, table[1:]))
    assert table[128] < 64  # mid grey needs far less than half duty


def test_gamma_identity():
    assert gamma_table(1.0) == list(range(256))
    assert apply_gamma([(10, 128, 255)], gamma_table(1.0)) == [(10, 128, 255)]


def test_current_estimate():
    assert estimate_ma([WHITE] * 60) == 60 * 60 + 60  # 60 mA white + 1 mA idle each
    assert estimate_ma([(0, 0, 0)] * 10) == 10


def test_limiter_scales_down_to_budget():
    frame = [WHITE] * 60
    limited, f = limit_current(frame, 1000)
    assert 0 < f < 1
    assert estimate_ma(limited) <= 1000
    assert estimate_ma(limited) > 950  # does not over-shoot by much


def test_limiter_leaves_small_frames_alone():
    frame = [(10, 20, 30)] * 60
    assert limit_current(frame, 1000) == (frame, 1.0)
    assert limit_current([WHITE] * 60, None)[1] == 1.0


def test_limiter_budget_below_idle_turns_everything_off():
    limited, f = limit_current([WHITE] * 100, 50)
    assert f == 0 and all(px == (0, 0, 0) for px in limited)


def test_brightness():
    assert apply_brightness([(200, 100, 0)], 0.5) == [(100, 50, 0)]
    assert apply_brightness([(200, 100, 0)], 2.0) == [(200, 100, 0)]


def test_output_stage():
    stage = OutputStage(brightness=1.0, max_ma=2000, gamma=2.6)
    out = stage.process([WHITE] * 256)
    assert out.limit < 1 and out.ma <= 2000
    assert len(out.hardware) == len(out.display) == 256
    dim = OutputStage(brightness=0.5, max_ma=None).process([WHITE])
    assert dim.display == [(127, 127, 127)] and dim.hardware[0][0] == 42  # 255 * 0.5 ** 2.6


def test_hsv_and_palette():
    assert hsv(0) == (255, 0, 0) and hsv(1 / 3) == (0, 255, 0) and hsv(0, 0, 1) == WHITE
    assert palette([(0, 0, 0), (200, 0, 0)], 0.25) == (100, 0, 0)


def test_serpentine():
    frame = [(i, 0, 0) for i in range(6)]
    assert [p[0] for p in serpentine(frame, 3)] == [0, 1, 2, 5, 4, 3]
