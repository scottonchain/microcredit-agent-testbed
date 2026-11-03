#!/usr/bin/env python3
"""Narration for one spec: one audio file per segment plus word timings.

Engine ladder (see coordination/MEDIA_PRODUCTION.md): a premium engine when its key
is present in the environment, otherwise Microsoft neural voices through edge-tts.
edge-tts talks to speech.platform.bing.com over a websocket; in the cloud container
that must go through the HTTPS proxy with its CA bundle, which this script sets.
Every call retries, because the service sometimes drops a first attempt.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import subprocess
import time

CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
if Path(CA_BUNDLE).exists():
    os.environ.setdefault("SSL_CERT_FILE", CA_BUNDLE)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", CA_BUNDLE)


def edge_tts(text, voice, rate, out_mp3, out_words, tries=4):
    """Microsoft neural voice through edge-tts, with word boundaries from the stream."""
    import edge_tts as et
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    async def once():
        comm = et.Communicate(text, voice, rate=rate, proxy=proxy, boundary="WordBoundary")
        audio, words = bytearray(), []
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
            elif chunk["type"] == "WordBoundary":
                words.append({"word": chunk["text"], "start": chunk["offset"] / 1e7,
                              "end": (chunk["offset"] + chunk["duration"]) / 1e7})
        return bytes(audio), words

    last = None
    for attempt in range(tries):
        try:
            audio, words = asyncio.run(once())
            if len(audio) > 1000 and words:
                out_mp3.write_bytes(audio)
                out_words.write_text(json.dumps(words))
                return
            last = "no audio or no word boundaries received"
        except Exception as exc:  # the service sometimes drops a first attempt
            last = repr(exc)
        time.sleep(2 * (attempt + 1))
    raise SystemExit(f"edge-tts failed for {voice}: {last}")


def leading_silence(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=n=-45dB:d=0.05",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"silence_start: (-?[\d.]+)\s*\n.*?silence_end: ([\d.]+)", r.stderr, re.S)
    if m and float(m.group(1)) <= 0.01:
        return max(0.0, float(m.group(2)) - 0.08)
    return 0.0


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text())
    voice = args.voice or spec["voice"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gap = spec.get("gap_seconds", 0.4)
    timeline = []
    t = 0.0
    for seg in spec["segments"]:
        mp3 = out / f"{seg['id']}.mp3"
        words_path = out / f"{seg['id']}.words.json"
        wav = out / f"{seg['id']}.wav"
        edge_tts(seg["speak"], voice, spec.get("rate", "+0%"), mp3, words_path)
        # trim outer quiet with short handles; keep word times on the trimmed clock
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", "48000", "-ac", "1",
                        "-af", "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,"
                               "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse",
                        str(wav)], check=True)
        lead = leading_silence(mp3)
        words = json.loads(words_path.read_text())
        for w in words:
            w["start"] = round(max(0.0, w["start"] - lead), 3)
            w["end"] = round(max(0.0, w["end"] - lead), 3)
        d = duration(wav)
        timeline.append({"id": seg["id"], "start": round(t, 3), "end": round(t + d, 3),
                         "duration": round(d, 3), "words": words})
        t += d + gap
    total = t - gap + spec.get("tail_seconds", 1.5)
    (out / "timeline.json").write_text(json.dumps(
        {"voice": voice, "engine": "edge-tts (Microsoft neural voices)", "rate": spec.get("rate", "+0%"),
         "total": round(total, 3), "segments": timeline}, indent=2))
    print(json.dumps({"voice": voice, "total_seconds": round(total, 2),
                      "segments": [(s["id"], s["duration"]) for s in timeline]}))


if __name__ == "__main__":
    main()
