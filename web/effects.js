// JavaScript port of the led-lights effects (same math as src/led_lights/effects).
// Each factory returns render(t, n, w, h) -> array of [r, g, b] (0..255).
(function (root) {
  "use strict";
  const clamp8 = (x) => (x <= 0 ? 0 : x >= 255 ? 255 : x | 0);
  const rgb = (r, g, b) => [clamp8(r), clamp8(g), clamp8(b)];
  const BLACK = [0, 0, 0];

  function hsv(h, s = 1, v = 1) {
    h = (((h % 1) + 1) % 1) * 6;
    const i = Math.floor(h) % 6, f = h - Math.floor(h);
    const p = v * (1 - s), q = v * (1 - s * f), u = v * (1 - s * (1 - f));
    const [r, g, b] = [[v, u, p], [q, v, p], [p, v, u], [p, q, v], [u, p, v], [v, p, q]][i];
    return rgb(r * 255 + 0.5, g * 255 + 0.5, b * 255 + 0.5);
  }
  const scale = (c, f) => rgb(c[0] * f, c[1] * f, c[2] * f);
  const add = (a, b) => rgb(a[0] + b[0], a[1] + b[1], a[2] + b[2]);
  const lerp = (a, b, t) => {
    t = Math.min(1, Math.max(0, t));
    return rgb(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
  };
  const smoothstep = (e0, e1, x) => {
    const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
    return t * t * (3 - 2 * t);
  };

  const PALETTES = {
    rainbow: [0, 1, 2, 3, 4, 5, 6, 7].map((i) => hsv(i / 8)),
    party: [[85, 0, 171], [132, 0, 124], [181, 0, 75], [229, 0, 27], [232, 23, 0], [184, 71, 0],
      [171, 119, 0], [171, 171, 0], [171, 85, 0], [221, 34, 0], [242, 0, 14], [194, 0, 62],
      [143, 0, 113], [95, 0, 161], [47, 0, 208], [0, 7, 249]],
    aurora: [[0, 255, 120], [0, 200, 160], [30, 120, 255], [140, 40, 255], [0, 230, 90]],
  };
  function palette(name, x) {
    const stops = PALETTES[name], n = stops.length;
    const pos = (((x % 1) + 1) % 1) * n, i = Math.floor(pos) % n;
    return lerp(stops[i], stops[(i + 1) % n], pos - Math.floor(pos));
  }
  function heatColor(heat) {
    const t192 = Math.floor((Math.min(255, Math.max(0, heat)) * 191) / 255);
    const ramp = (t192 & 0x3f) << 2;
    if (t192 & 0x80) return [255, 255, ramp];
    if (t192 & 0x40) return [255, ramp, 0];
    return [ramp, 0, 0];
  }

  // Integer hash -> 0..1 (same constants as the Python version).
  function hash(ix, iy, seed) {
    let n = (Math.imul(ix, 374761393) + Math.imul(iy, 668265263) + Math.imul(seed, 982451653)) >>> 0;
    n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0;
    return ((n ^ (n >>> 16)) & 0xffff) / 65535;
  }
  function noise2(x, y, seed) {
    const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const a = hash(ix, iy, seed), b = hash(ix + 1, iy, seed);
    const c = hash(ix, iy + 1, seed), d = hash(ix + 1, iy + 1, seed);
    const top = a + (b - a) * sx, bottom = c + (d - c) * sx;
    return top + (bottom - top) * sy;
  }
  function fbm(x, y, octaves, seed) {
    let total = 0, amp = 1, norm = 0;
    for (let o = 0; o < octaves; o++) {
      total += noise2(x, y, seed + o) * amp; norm += amp; x *= 2; y *= 2; amp *= 0.5;
    }
    return total / norm;
  }
  const rand = Math.random;
  const randint = (a, b) => a + Math.floor(rand() * (b - a + 1));
  const fill = (n, f) => Array.from({ length: n }, (_, i) => f(i));

  // Wraps a stateful effect: (re)creates state when the size changes and passes dt.
  function stateful(init, draw) {
    return () => {
      let state = null, key = "", last = 0;
      return (t, n, w, h) => {
        if (key !== `${n}x${w}`) { key = `${n}x${w}`; state = init(n, w, h); last = t; }
        const dt = Math.min(0.1, Math.max(0, t - last)); last = t;
        return draw(state, t, dt, n, w, h);
      };
    };
  }

  const EFFECTS = {
    rainbow: { matrix: false, create: () => (t, n) => fill(n, (i) => hsv(i / n - t * 0.25)) },

    comet: { matrix: false, create: () => (t, n) => {
      const tail = Math.max(3, n / 5), period = Math.max(1, n / 40);
      const phase = (t / period) % 2, fwd = phase < 1;
      const pos = (fwd ? phase : 2 - phase) * (n - 1), color = hsv(t * 0.05);
      return fill(n, (i) => {
        const d = fwd ? pos - i : i - pos;
        let b = 0;
        if (d > -1 && d < 0) b = 1 + d; else if (d >= 0 && d < tail) b = (1 - d / tail) ** 2;
        let c = scale(color, b);
        if (d >= 0 && d < 1) c = add(c, scale([255, 255, 255], 0.6 * (1 - d)));
        return c;
      });
    } },

    fire: { matrix: false, create: stateful(
      (n) => ({ heat: new Float32Array(n), acc: 0 }),
      (s, t, dt, n) => {
        s.acc += dt;
        while (s.acc >= 1 / 60) {
          s.acc -= 1 / 60;
          for (let i = 0; i < n; i++) s.heat[i] = Math.max(0, s.heat[i] - randint(0, Math.floor(550 / n) + 2));
          for (let k = n - 1; k > 1; k--) s.heat[k] = (s.heat[k - 1] + 2 * s.heat[k - 2]) / 3;
          if (randint(0, 255) < 120) { const y = randint(0, Math.min(6, n - 1)); s.heat[y] = Math.min(255, s.heat[y] + randint(160, 255)); }
        }
        return Array.from(s.heat, heatColor);
      }) },

    twinkle: { matrix: false, create: () => {
      const colors = [[255, 220, 160], [160, 200, 255], [255, 255, 255], [255, 180, 80]];
      return (t, n) => fill(n, (i) => {
        const v = Math.sin(2 * Math.PI * (t / (1.5 + 3 * hash(i, 1, 7)) + hash(i, 2, 7)));
        const b = Math.max(0, (v - 0.55) / 0.45) ** 2;
        return add([0, 0, 6], scale(colors[Math.floor(hash(i, 3, 7) * 4) % 4], b));
      });
    } },

    breathing: { matrix: false, create: () => (t, n) => {
      const b = (Math.exp(Math.sin((t * 2 * Math.PI) / 4)) - 1 / Math.E) / (Math.E - 1 / Math.E);
      const c = hsv(0.55 + 0.15 * Math.sin(t * 0.2), 0.8, 0.05 + 0.95 * b);
      return fill(n, () => c);
    } },

    color_wipe: { matrix: false, create: () => {
      const colors = [[255, 0, 40], [255, 140, 0], [0, 220, 80], [0, 120, 255], [160, 0, 255]];
      return (t, n) => {
        const dur = Math.max(0.5, n / 50), k = Math.floor(t / dur), progress = ((t % dur) / dur) * n;
        const nw = colors[k % 5], old = colors[(k + 4) % 5];
        return fill(n, (i) => lerp(old, nw, progress - i));
      };
    } },

    theater_chase: { matrix: false, create: () => (t, n) => {
      const step = Math.floor(t * 12);
      return fill(n, (i) => ((i + step) % 3 === 0 ? hsv(i / n + t * 0.1) : BLACK));
    } },

    plasma: { matrix: false, create: () => (t, n) => fill(n, (i) => {
      const v = Math.sin(i * 0.15 + t * 1.1) + Math.sin(i * 0.07 - t * 1.7) + Math.sin(i * 0.23 + Math.sin(t * 0.5) * 3);
      return palette("party", (v + 3) / 6 + t * 0.05);
    }) },

    aurora: { matrix: false, create: () => (t, n) => fill(n, (i) => {
      const x = (i / Math.max(1, n)) * 5;
      const b = smoothstep(0.35, 0.8, fbm(x + t * 0.12, t * 0.25, 3, 11));
      return add([0, 2, 4], scale(palette("aurora", fbm(x * 0.4, t * 0.08 + 50, 2, 3) * 1.5), b));
    }) },

    meteor_rain: { matrix: false, create: stateful(
      (n) => ({ buf: fill(n, () => [0, 0, 0]), pos: 0, color: hsv(rand(), 0.3), acc: 0 }),
      (s, t, dt, n) => {
        s.acc += dt;
        while (s.acc >= 1 / 60) {
          s.acc -= 1 / 60;
          for (const px of s.buf) if (rand() < 0.5) for (let c = 0; c < 3; c++) px[c] *= 0.8;
          s.pos += Math.max(30, n * 0.8) / 60;
          if (s.pos > n * 1.6) { s.pos = 0; s.color = hsv(rand(), 0.3); }
          for (let j = 0; j < 4; j++) { const k = Math.floor(s.pos) - j; if (k >= 0 && k < n) s.buf[k] = s.color.slice(); }
        }
        return s.buf.map((p) => rgb(p[0], p[1], p[2]));
      }) },

    bouncing_balls: { matrix: false, create: () => {
      const g = 9.81, colors = [[255, 40, 0], [0, 160, 255], [120, 255, 0], [255, 0, 200]];
      const launch = () => Math.sqrt(2 * g * (0.6 + 0.4 * rand()));
      return stateful(
        (n) => fill(n < 30 ? 3 : 4, (i) => ({ h: 0, v: launch(), e: 0.92 - 0.04 * i })),
        (balls, t, dt, n) => {
          for (let s = 0; s < 4; s++) for (const b of balls) {
            b.v -= (g * dt) / 4; b.h += (b.v * dt) / 4;
            if (b.h < 0) { b.h = 0; b.v = -b.v * b.e; if (b.v < 1.2) b.v = launch(); }
          }
          const out = fill(n, () => BLACK);
          balls.forEach((b, i) => {
            const p = Math.min(1, b.h) * (n - 1), k = Math.floor(p), f = p - k, c = colors[i % 4];
            out[k] = add(out[k], scale(c, 1 - f));
            if (k + 1 < n) out[k + 1] = add(out[k + 1], scale(c, f));
          });
          return out;
        })();
    } },

    heartbeat: { matrix: false, create: () => {
      const env = (t) => {
        const p = ((t % (60 / 72)) + 60 / 72) % (60 / 72);
        return Math.exp(-(((p - 0.05) / 0.045) ** 2)) + 0.6 * Math.exp(-(((p - 0.28) / 0.06) ** 2));
      };
      return (t, n) => {
        const mid = (n - 1) / 2;
        return fill(n, (i) => {
          const d = Math.abs(i - mid) / Math.max(1, mid), b = env(t - d * 0.25) * (1 - 0.6 * d);
          return rgb(255 * b, 10 * b, 25 * b);
        });
      };
    } },

    plasma2d: { matrix: true, create: () => (t, n, w, h) => {
      const k = 16 / Math.max(w, h), out = [];
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const X = x * k, Y = y * k, cx = X - 8 + 4 * Math.sin(t * 0.5), cy = Y - 8 + 4 * Math.cos(t * 0.3);
        const v = Math.sin(X * 0.4 + t) + Math.sin((Y * 0.3 - t) * 1.3) + Math.sin((X + Y) * 0.25 + t * 0.7)
          + Math.sin(Math.hypot(cx, cy) * 0.6 - t * 1.5);
        out.push(palette("rainbow", (v + 4) / 8 + t * 0.03));
      }
      return out;
    } },

    matrix_rain: { matrix: true, create: () => {
      const drop = (h, initial) => ({ y: -rand() * h * (initial ? 1.5 : 0.8), v: 6 + 8 * rand() });
      return stateful(
        (n, w, h) => ({ buf: new Float32Array(w * h), drops: fill(w, () => drop(h, true)) }),
        (s, t, dt, n, w, h) => {
          const fade = 0.02 ** dt, heads = new Set();
          for (let i = 0; i < s.buf.length; i++) s.buf[i] *= fade;
          s.drops.forEach((d, x) => {
            const prev = Math.floor(d.y);
            d.y += d.v * dt;
            for (let y = Math.max(0, prev); y < Math.min(h, Math.floor(d.y) + 1); y++) s.buf[y * w + x] = 1;
            if (d.y >= 0 && d.y < h) heads.add(Math.floor(d.y) * w + x);
            if (d.y >= h + 2) s.drops[x] = drop(h, false);
          });
          return Array.from(s.buf, (v, i) => (heads.has(i) ? [180, 255, 180] : rgb(0, 255 * v, 40 * v * v)));
        })();
    } },

    life: { matrix: true, create: () => {
      const seed = (w, h) => ({ age: fill(w * h, () => (rand() < 0.35 ? 1 : 0)), hist: [], gens: 0 });
      return stateful(
        (n, w, h) => ({ ...seed(w, h), acc: 0 }),
        (s, t, dt, n, w, h) => {
          s.acc += dt;
          while (s.acc >= 0.15) {
            s.acc -= 0.15;
            const nxt = new Array(w * h).fill(0);
            for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
              let alive = 0;
              for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++)
                if ((dx || dy) && s.age[((y + dy + h) % h) * w + ((x + dx + w) % w)]) alive++;
              const i = y * w + x;
              if (s.age[i] && (alive === 2 || alive === 3)) nxt[i] = s.age[i] + 1;
              else if (!s.age[i] && alive === 3) nxt[i] = 1;
            }
            s.age = nxt; s.gens++;
            const key = nxt.map((a) => (a ? 1 : 0)).join("");
            if (!nxt.some(Boolean) || s.hist.includes(key) || s.gens > 300) Object.assign(s, seed(w, h));
            else s.hist = [...s.hist, key].slice(-4);
          }
          return s.age.map((a) => (a ? hsv(0.35 + Math.min(a, 30) / 40, 0.9, 1) : BLACK));
        })();
    } },

    spiral: { matrix: true, create: () => (t, n, w, h) => {
      const cx = (w - 1) / 2, cy = (h - 1) / 2, k = 16 / Math.max(w, h), out = [];
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const a = Math.atan2(y - cy, x - cx), r = Math.hypot(x - cx, y - cy) * k;
        const b = 0.5 + 0.5 * Math.sin(3 * a + r * 0.7 - t * 4);
        out.push(scale(hsv(a / (2 * Math.PI) + r * 0.03 + t * 0.1), b * b));
      }
      return out;
    } },
  };

  // Output stage: brightness -> gamma -> current limit (WS2812B: ~20 mA per channel, ~1 mA idle).
  function gammaTable(g) { return fill(256, (i) => Math.round(255 * (i / 255) ** g)); }
  function output(frame, brightness, maxMa, table, gamma) {
    const dimmed = frame.map((c) => scale(c, brightness));
    const hw = dimmed.map((c) => [table[c[0]], table[c[1]], table[c[2]]]);
    const idle = hw.length;
    const ma = idle + (hw.reduce((s, c) => s + c[0] + c[1] + c[2], 0) / 255) * 20;
    let f = 1;
    if (maxMa && ma > maxMa) f = Math.max(0, (maxMa - idle) / (ma - idle));
    const display = f < 1 ? dimmed.map((c) => scale(c, f ** (1 / gamma))) : dimmed;
    return { display, ma: f < 1 ? idle + (ma - idle) * f : ma, limit: f };
  }

  root.LedLights = { EFFECTS, output, gammaTable };
})(typeof window !== "undefined" ? window : globalThis);
