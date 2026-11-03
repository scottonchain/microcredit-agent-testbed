#!/usr/bin/env python3
"""Build one short video from a spec: narration, frames, music bed, mix, master, captions, QA.

    python3 tools/media/make.py tools/media/spec.json --out build/omnequa-try-30s

Steps can be rerun separately (tts.py, render.py, music.py). The result is
<out>/<slug>.mp4 (H.264 + AAC, 1080p30, -14 LUFS, -1 dBTP), <out>/<slug>.vtt,
<out>/<slug>.provenance.json and <out>/qa.json. See coordination/MEDIA_PRODUCTION.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw)


def loudnorm_stats(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "loudnorm=I=-14:TP=-1.6:LRA=9:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    return json.loads(r.stderr[r.stderr.rfind("{"):])


def write_vtt(spec, timeline, out):
    cues = []
    for seg in timeline["segments"]:
        s = next(x for x in spec["segments"] if x["id"] == seg["id"])
        import re
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", s["caption"]) if x.strip()]
        spoken = [x.strip() for x in re.split(r"(?<=[.!?])\s+", s["speak"]) if x.strip()]
        wi = 0
        for k, sp in enumerate(spoken):
            n = len(sp.split())
            a = seg["words"][wi] if wi < len(seg["words"]) else None
            b = seg["words"][min(wi + n - 1, len(seg["words"]) - 1)] if seg["words"] else None
            start = seg["start"] + (a["start"] if a else 0)
            end = seg["start"] + (b["end"] if b else seg["duration"])
            cues.append((start, end + 0.3, sents[k] if k < len(sents) else sents[-1]))
            wi += n
    def ts(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    lines = ["WEBVTT", ""]
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{ts(a)} --> {ts(b)}", text, ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--skip-tts", action="store_true", help="reuse <out>/tts")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text())
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    slug = spec["slug"]
    tts_dir = out / "tts"
    if not args.skip_tts:
        cmd = [sys.executable, HERE / "tts.py", args.spec, "--out", tts_dir]
        if args.voice:
            cmd += ["--voice", args.voice]
        print(run(cmd).stdout)
    timeline = json.loads((tts_dir / "timeline.json").read_text())
    total = timeline["total"]

    # 1. narration track: segments placed at their timeline starts, then levelled
    inputs, filters = [], []
    for i, seg in enumerate(timeline["segments"]):
        inputs += ["-i", str(tts_dir / f"{seg['id']}.wav")]
        filters.append(f"[{i}:a]adelay={int(seg['start'] * 1000)}|{int(seg['start'] * 1000)}[a{i}]")
    n = len(timeline["segments"])
    filters.append("".join(f"[a{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad=whole_dur={total}[voice]")
    voice_wav = out / "voice.wav"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters), "-map", "[voice]",
         "-t", str(total), "-ar", "48000", "-ac", "1", str(voice_wav)])
    st = loudnorm_stats(voice_wav)
    voice_norm = out / "voice-norm.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(voice_wav), "-af",
         f"loudnorm=I=-16:TP=-1.5:LRA=9:linear=true:measured_I={st['input_i']}:measured_TP={st['input_tp']}"
         f":measured_LRA={st['input_lra']}:measured_thresh={st['input_thresh']}:offset={st['target_offset']},"
         "highpass=f=70,deesser", "-ar", "48000", str(voice_norm)])

    # 2. music bed, ducked under the voice
    use_music = spec.get("music", {}).get("enabled", True) and not args.no_music
    mix_wav = out / "mix.wav"
    if use_music:
        music_wav = out / "music.wav"
        run([sys.executable, HERE / "music.py", "--seconds", str(total), "--out", str(music_wav)])
        bed = spec["music"].get("bed_lufs", -30)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(voice_norm), "-i", str(music_wav), "-filter_complex",
             f"[1:a]loudnorm=I={bed}:TP=-6:LRA=6[m];[m][0:a]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600[md];"
             "[0:a][md]amix=inputs=2:normalize=0[out]", "-map", "[out]", "-ar", "48000", "-ac", "2", str(mix_wav)])
    else:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(voice_norm), "-ac", "2", str(mix_wav)])
    st = loudnorm_stats(mix_wav)
    master = out / "master.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(mix_wav), "-af",
         f"loudnorm=I=-14:TP=-1.6:LRA=9:linear=true:measured_I={st['input_i']}:measured_TP={st['input_tp']}"
         f":measured_LRA={st['input_lra']}:measured_thresh={st['input_thresh']}:offset={st['target_offset']}",
         "-ar", "48000", str(master)])

    # 3. frames
    video = out / "video.mp4"
    print(run([sys.executable, HERE / "render.py", args.spec, "--timeline", tts_dir / "timeline.json", "--out", video]).stdout)

    # 4. mux, captions, provenance, QA
    final = out / f"{slug}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(master), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(final)])
    write_vtt(spec, timeline, out / f"{slug}.vtt")
    prov = {
        "title": spec["title"], "file": final.name, "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
        "voice": timeline["voice"], "engine": timeline["engine"], "synthetic_voice": True, "cloned_real_person": False,
        "music": "original generated bed (tools/media/music.py), no samples" if use_music else "none",
        "screens": sorted(p.name for p in (HERE / "assets/try").glob("*.png")),
        "spoken_text": [s["speak"] for s in spec["segments"]],
        "human_listening_review": "pending: the operator reviews before any publication",
    }
    (out / f"{slug}.provenance.json").write_text(json.dumps(prov, indent=2))
    qa = run([sys.executable, HERE / "qa.py", str(final), "--vtt", str(out / f"{slug}.vtt"), "--max-seconds", "32"]).stdout
    (out / "qa.json").write_text(qa)
    print(qa)


if __name__ == "__main__":
    main()
