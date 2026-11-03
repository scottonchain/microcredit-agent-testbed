#!/usr/bin/env python3
"""Measured checks on a finished video. Exit 1 on any failure. This is not a listening review."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--vtt")
    ap.add_argument("--max-seconds", type=float, default=35)
    ap.add_argument("--min-seconds", type=float, default=15)
    a = ap.parse_args()
    info = probe(a.video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = next(s for s in info["streams"] if s["codec_type"] == "audio")
    dur = float(info["format"]["duration"])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", a.video, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    tail = r.stderr[-1500:]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))
    lra = float(re.search(r"LRA:\s+(-?[\d.]+) LU", tail).group(1))
    black = subprocess.run(["ffmpeg", "-hide_banner", "-i", a.video, "-vf", "blackdetect=d=0.5:pix_th=0.05", "-an", "-f", "null", "-"],
                           capture_output=True, text=True).stderr.count("black_start")
    checks = {
        "duration_in_range": a.min_seconds <= dur <= a.max_seconds,
        "video_1080p_h264": v["codec_name"] == "h264" and int(v["height"]) >= 1080 and v["pix_fmt"] == "yuv420p",
        "audio_aac_48k_stereo": au["codec_name"] == "aac" and au["sample_rate"] == "48000" and int(au["channels"]) == 2,
        "loudness_near_minus_14_lufs": -15.5 <= lufs <= -12.5,
        "true_peak_at_or_below_minus_1": tp <= -0.9,
        "no_black_holds": black == 0,
        "captions_present": bool(a.vtt and Path(a.vtt).exists() and "-->" in Path(a.vtt).read_text()),
    }
    result = {"file": a.video, "seconds": round(dur, 2), "width": v["width"], "height": v["height"],
              "fps": v.get("avg_frame_rate"), "integrated_lufs": lufs, "true_peak_dbtp": tp, "lra_lu": lra,
              "checks": checks, "ok": all(checks.values())}
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
