"""The frame loop: render -> output stage -> backend, at a fixed frame rate."""

from __future__ import annotations

import time

from .effects import Effect
from .power import OutputStage


def run(effect: Effect, backend, stage: OutputStage, leds: int, fps: float = 60.0,
        duration: float | None = None) -> int:
    """Run until Ctrl+C or `duration` seconds. Returns the number of frames shown."""
    period = 1.0 / fps
    start = time.perf_counter()
    deadline = start
    frames = 0
    try:
        while True:
            t = time.perf_counter() - start
            if duration is not None and t >= duration:
                break
            # Effects get real elapsed time, so speed is independent of fps.
            backend.show(stage.process(effect.render(t, leds)))
            frames += 1
            deadline += period
            sleep = deadline - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)
            else:
                deadline = time.perf_counter()  # running late: don't try to catch up
    except KeyboardInterrupt:
        pass
    finally:
        backend.close()
    return frames
