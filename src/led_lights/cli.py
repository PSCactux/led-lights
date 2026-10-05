"""Command line interface: `led-lights list | run | gif | gallery`."""

from __future__ import annotations

import argparse
from pathlib import Path

from .effects import EFFECTS, get_effect
from .power import OutputStage


def _leds(args, effect) -> int:
    return args.leds or effect.default_leds


def cmd_list(args) -> None:
    for name, cls in EFFECTS.items():
        kind = "matrix" if cls.matrix else "strip"
        print(f"{name:16} {kind:7} {cls.description}")


def cmd_run(args) -> None:
    from .runner import run

    effect = get_effect(args.effect, seed=args.seed, width=args.width)
    leds = _leds(args, effect)
    width = (args.width or None) if effect.matrix else None
    if effect.matrix and not width:
        effect.render(0.0, leds)  # resolves the default (square) width
        width = effect.w
    stage = OutputStage(brightness=args.brightness, max_ma=args.max_ma or None, gamma=args.gamma)
    if args.backend == "rpi":
        from .backends.rpi import RpiBackend
        backend = RpiBackend(leds, pin=args.pin, matrix_width=width, zigzag=args.zigzag)
    else:
        from .backends.sim import TerminalBackend
        backend = TerminalBackend(width=width)
    frames = run(effect, backend, stage, leds, fps=args.fps, duration=args.duration)
    print(f"{frames} frames")


def _render(name: str, out: Path, args) -> Path:
    from .backends.sim import render_frames, save_gif, save_timeline

    effect = get_effect(name, seed=args.seed, width=args.width)
    leds = _leds(args, effect)
    seconds = args.seconds or effect.gif_seconds
    frames = render_frames(effect, leds, seconds, args.fps)
    if out.suffix.lower() == ".png":
        return save_timeline(frames, out)
    return save_gif(frames, out, args.fps, width=effect.w if effect.matrix else None, cell=args.cell)


def cmd_gif(args) -> None:
    out = Path(args.output or f"out/{args.effect}.gif")
    print(_render(args.effect, out, args))


def cmd_gallery(args) -> None:
    out_dir = Path(args.out)
    for name in EFFECTS:
        print(_render(name, out_dir / f"{name}.gif", args))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="led-lights", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list effects").set_defaults(func=cmd_list)

    def common(sp):
        sp.add_argument("--leds", type=int, default=None, help="LED count (default: 60, or 256 for matrix effects)")
        sp.add_argument("--width", type=int, default=None, help="matrix width (default: sqrt(leds))")
        sp.add_argument("--seed", type=int, default=1234, help="random seed for stochastic effects")

    r = sub.add_parser("run", help="run an effect live")
    r.add_argument("effect", choices=list(EFFECTS))
    common(r)
    r.add_argument("--backend", choices=["sim", "rpi"], default="sim")
    r.add_argument("--fps", type=float, default=60.0)
    r.add_argument("--brightness", type=float, default=0.6, help="0..1, perceptual")
    r.add_argument("--max-ma", type=float, default=2000.0, help="current budget in mA (0 = no limit)")
    r.add_argument("--gamma", type=float, default=2.6)
    r.add_argument("--duration", type=float, default=None, help="stop after N seconds")
    r.add_argument("--pin", type=int, default=18, help="rpi: GPIO data pin")
    r.add_argument("--zigzag", action="store_true", help="rpi: serpentine-wired matrix")
    r.set_defaults(func=cmd_run)

    g = sub.add_parser("gif", help="render an effect to a GIF (or a space-time .png)")
    g.add_argument("effect", choices=list(EFFECTS))
    g.add_argument("-o", "--output", help="output path, .gif or .png (default: out/<effect>.gif)")
    common(g)
    g.add_argument("--seconds", type=float, default=None)
    g.add_argument("--fps", type=float, default=25.0)
    g.add_argument("--cell", type=int, default=12, help="pixels per LED")
    g.set_defaults(func=cmd_gif)

    a = sub.add_parser("gallery", help="render every effect to a GIF")
    a.add_argument("--out", default="docs/gifs")
    common(a)
    a.add_argument("--seconds", type=float, default=None)
    a.add_argument("--fps", type=float, default=20.0)
    a.add_argument("--cell", type=int, default=10, help="pixels per LED (small keeps the README light)")
    a.set_defaults(func=cmd_gallery)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
