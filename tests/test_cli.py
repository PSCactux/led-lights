from led_lights.cli import main


def test_list(capsys):
    main(["list"])
    out = capsys.readouterr().out
    assert "fire" in out and "life" in out


def test_gif_and_timeline(tmp_path):
    gif = tmp_path / "comet.gif"
    main(["gif", "comet", "-o", str(gif), "--seconds", "0.4", "--leds", "20"])
    assert gif.read_bytes()[:6] == b"GIF89a"
    png = tmp_path / "fire.png"
    main(["gif", "fire", "-o", str(png), "--seconds", "0.4"])
    assert png.read_bytes()[:4] == b"\x89PNG"


def test_run_sim_for_a_moment(capsys):
    main(["run", "spiral", "--duration", "0.2", "--fps", "30"])
    assert "frames" in capsys.readouterr().out
