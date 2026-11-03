#!/usr/bin/env python3
"""Render scene.html frame by frame with Playwright and pipe the frames into ffmpeg.

Deterministic: each frame is window.seek(t) then a screenshot, so motion never
depends on real-time playback. Output is an H.264 video track with no audio.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=1.0, help="device scale factor (1 is 1920x1080)")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text())
    timeline = json.loads(Path(args.timeline).read_text())
    fps = spec["fps"]
    frames = int(round(timeline["total"] * fps))
    w, h = spec["width"], spec["height"]
    driver = HERE / "render_frames.js"
    driver.write_text(r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [specPath, tlPath, frames, fps, scale, w, h] = process.argv.slice(2);
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const tl = JSON.parse(fs.readFileSync(tlPath, 'utf8'));
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: +scale });
  const p = await ctx.newPage();
  await p.goto('file://' + __dirname + '/scene.html');
  await p.evaluate(([s, t]) => window.setup(s, t), [spec, tl]);
  await p.evaluate(() => document.fonts.ready);
  for (let i = 0; i < +frames; i++) {
    await p.evaluate(t => window.seek(t), i / +fps);
    const png = await p.screenshot({ type: 'png' });
    process.stdout.write(png);
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
""")
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-vcodec", "png", "-framerate", str(fps),
                           "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                           "-vf", f"scale={w}:{h}", "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    node = subprocess.Popen(["node", str(driver), args.spec, args.timeline, str(frames), str(fps), str(args.scale),
                             str(w), str(h)], stdout=ff.stdin, stderr=sys.stderr)
    node.wait()
    ff.stdin.close()
    ff.wait()
    if node.returncode or ff.returncode:
        raise SystemExit("render failed")
    print(json.dumps({"frames": frames, "fps": fps, "out": args.out}))


if __name__ == "__main__":
    main()
