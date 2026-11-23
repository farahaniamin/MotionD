"""Procedurally synthesize a small paper foley bank (resources/sfx/paper/*.flac) for the paper_cut style.
These are serviceable placeholders; drop real recorded paper foley with the same names to upgrade."""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def band(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def env(n, a, r, shape=2.0):
    t = np.linspace(0, 1, n)
    na = max(1, int(a * n))
    e = np.ones(n)
    e[:na] = np.linspace(0, 1, na) ** 0.6
    e[na:] = (1 - np.linspace(0, 1, n - na)) ** shape
    return e * (1 if r else 1)


def crackle(n, density):
    c = np.zeros(n)
    idx = rng.integers(0, n, int(density * n / SR))
    c[idx] = rng.uniform(0.3, 1.0, len(idx)) * rng.choice([-1, 1], len(idx))
    return band(c, 1500, 9000)


def slide(dur, lo, hi, seed):
    n = int(dur * SR)
    x = band(rng.standard_normal(n), lo, hi)
    grain = 0.6 + 0.4 * np.abs(band(rng.standard_normal(n), 2, 30)) * 6
    y = x * grain * env(n, 0.45, True, 1.6) + crackle(n, 900) * 0.25 * env(n, 0.3, True)
    return y


def tap(lo_mix=1.0):
    n = int(0.16 * SR)
    thump = band(rng.standard_normal(n), 60, 380) * env(n, 0.02, True, 6) * lo_mix * 2.2
    snap = band(rng.standard_normal(n), 2500, 9000) * env(n, 0.005, True, 14) * 0.7
    return thump + snap


def flap():
    n = int(0.24 * SR)
    t = np.arange(n) / SR
    am = (np.sin(2 * np.pi * 26 * t) > 0.2).astype(float)
    return band(rng.standard_normal(n), 900, 7000) * am * env(n, 0.1, True, 2)


def slap():
    n = int(0.3 * SR)
    hit = band(rng.standard_normal(n), 300, 8000) * env(n, 0.004, True, 10) * 1.4
    body = band(rng.standard_normal(n), 70, 260) * env(n, 0.01, True, 5) * 1.8
    return hit + body


def tear():
    n = int(0.62 * SR)
    base = band(rng.standard_normal(n), 1800, 7500) * 0.35
    return (base + crackle(n, 5200) * 1.1) * env(n, 0.15, True, 1.2)


def write(path: Path, y):
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.89
    st = np.stack([y, np.roll(y, 9) * 0.97], 1)
    pcm = (st * 32767).astype("<i2")
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), str(path)], check=True)
    wav.unlink()


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "resources/sfx/paper")
    out.mkdir(parents=True, exist_ok=True)
    bank = {
        "slide_1": slide(0.42, 700, 6500, 1),
        "slide_2": slide(0.36, 900, 8000, 2),
        "slide_3": slide(0.5, 500, 5000, 3),
        "tap_1": tap(1.0),
        "tap_2": tap(0.7),
        "flap": flap(),
        "slap": slap(),
        "tear": tear(),
    }
    for k, y in bank.items():
        write(out / f"{k}.flac", y)
        print(f"[SFX] {out / k}.flac")


if __name__ == "__main__":
    main()
