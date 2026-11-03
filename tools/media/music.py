#!/usr/bin/env python3
"""A quiet, original ambient bed: detuned pad chords, low-passed, with a soft room.

No samples, no borrowed tune. It sits far under the voice (see spec music.bed_lufs)
and is ducked by the mix. Deterministic for a given length and seed.
"""
import argparse
import math
import wave

import numpy as np

SR = 48000


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def pad_note(freq, n, sr=SR):
    t = np.arange(n) / sr
    out = np.zeros(n)
    for det in (-0.35, 0.0, 0.35):          # three slightly detuned voices
        f = freq * 2 ** (det / 1200 * 8)
        # soft saw: first few harmonics with 1/k falloff, then a slow low-pass
        for k in range(1, 7):
            out += (1.0 / k) * np.sin(2 * math.pi * f * k * t + det * 7)
    return out / 18.0


def lowpass(x, cutoff, sr=SR):
    a = math.exp(-2 * math.pi * cutoff / sr)
    y = np.zeros_like(x)
    acc = 0.0
    b = 1 - a
    for i in range(len(x)):
        acc = a * acc + b * x[i]
        y[i] = acc
    return y


def room(x, sr=SR):
    y = x.copy()
    for delay_ms, gain in ((97, 0.32), (151, 0.26), (223, 0.2), (331, 0.14)):
        d = int(sr * delay_ms / 1000)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += gain * buf
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    n = int(args.seconds * SR)
    # Four slow chords, 8 s each, looping: Cmaj9, Am7, Fmaj7, G6 (voiced low and open)
    chords = [[48, 55, 59, 62, 67], [45, 52, 55, 59, 64], [41, 48, 52, 57, 64], [43, 50, 55, 59, 64]]
    bar = 8 * SR
    mix = np.zeros(n)
    i = 0
    while i < n:
        chord = chords[(i // bar) % len(chords)]
        length = min(bar + SR, n - i)          # one second of overlap between chords
        seg = np.zeros(length)
        for note in chord:
            seg += pad_note(midi(note), length)
        t = np.arange(length) / SR
        env = np.minimum(t / 2.5, 1.0) * np.minimum((length / SR - t) / 2.0, 1.0)
        mix[i:i + length] += seg * env
        i += bar
    mix = lowpass(lowpass(mix, 900), 900)
    mix = room(mix)
    fade = np.ones(n)
    f_in = int(2.0 * SR)
    f_out = int(2.5 * SR)
    fade[:f_in] = np.linspace(0, 1, f_in)
    fade[-f_out:] = np.linspace(1, 0, f_out)
    mix *= fade
    mix /= max(1e-9, np.max(np.abs(mix))) / 0.5
    stereo = np.stack([mix, np.roll(mix, int(0.0007 * SR))], axis=1)
    pcm = (stereo * 32767).astype(np.int16)
    with wave.open(args.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(args.out, round(n / SR, 2), "s")


if __name__ == "__main__":
    main()
