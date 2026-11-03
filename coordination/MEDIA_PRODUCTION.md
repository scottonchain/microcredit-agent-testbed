# Media production: short video and audio

Claude (AI), November 3, 2026, on the operator's direction of the same day: the
team's video and audio so far were "extremely poor", below NotebookLM, and the
operator wants 20 to 30 second walkthroughs with an app explainer and a vision
statement, at a professional level, for lay audiences. This page is the standard,
the diagnosis, the pipeline and the gates. It replaces the production parts of
the "Team audio" rules in the vision repository's CLAUDE.md (patch in
[media/vision-CLAUDE-team-media.patch](media/vision-CLAUDE-team-media.patch));
the editorial parts there (disclosure, claims, holds, categories, feed) still apply.

Measurable outcome: a lay viewer understands the vision and the app from one
30 second piece and goes to the Try page. Evidence sought: the operator's written
approval of a cut on first or second round, then Try page visits and feedback per
published piece. Competing simpler route: the written walkthrough post with
screenshots, which already exists and stays canonical. Stop or change condition:
two consecutive cuts that need more than one revision round on the voice mean the
engine changes (premium key), not another tuning pass; a published piece that
brings no tester in 30 days is not followed by a sequel in the same format.

## Diagnosis: why the earlier productions were poor

The committed productions are two episodes of "Two Agents, No Collateral" in the
vision repository (`audio/`, `editorial/audio/episode-1/`) and the theme they share.
No video exists in any repository; the video artefacts the operator saw were made
ad hoc inside sessions, uncommitted and unrepeatable. Seven causes, all visible
in the files:

1. **Nobody could hear the result.** Both provenance files say no member of the
   team can listen. Quality control was a Whisper transcription compared with the
   script, which proves the words and nothing about delivery, pacing or tone. A
   production could pass every check and still sound like 2010.
2. **The engine was chosen by what was reachable, not by quality.** Episode 2 used
   Kokoro-82M on a CPU because the premium route "was not reachable from this
   production environment". Episode 1 used a premium model but delivered it as
   64 kbps mono.
3. **The theme was eleven sine-wave notes generated in numpy** (`make_theme.py`), a
   ringtone, and it opened every episode.
4. **The format was the hardest one to fake.** A 47-turn two-voice banter with
   scripted jokes and "light disagreement" exposes every flaw of unacted
   text-to-speech. NotebookLM's two-host format works because it runs on a
   dialogue-trained speech model with acted interjections; we had no such model.
5. **The technical floor was a podcast minimum.** Mono, 64 to 96 kbps, loudness
   range 2 to 4 LU, no stereo bed, no mastering beyond loudnorm.
6. **No visual pipeline existed.** Nothing rendered motion, captions or real app
   screens; nothing was versioned, so nothing could improve run over run.
7. **The rules had no quality bar.** The vision CLAUDE.md audio section fixed length,
   disclosure, holds, feed mechanics and owners, and said nothing about what good
   sounds or looks like, had no reference, and had no audition or review gate.

## The standard

The floor is a NotebookLM Video Overview. A piece meets the bar when, in 20 to 30
seconds, a lay viewer gets the vision in one line, sees the real app do the thing,
hears one concept in one sentence, and is told where to try it, with nothing in
it that sounds or looks synthetic to a casual listener. Concretely:

- **One narrator voice** per series, cast by the operator from samples, measured
  pace (about 150 words a minute), no banter. Dialogue only when a
  dialogue-trained engine is in hand and a 20 second audition has passed.
- **Script of at most 90 words**: hook (one line), vision (one idea), walkthrough
  (three or four real screens, one label each), concept (one sentence), close
  (URL and disclosure). Plain words, one idea per sentence, no jargon.
- **Visuals**: the project palette (cream paper, dark ink, amber, teal), Inter,
  real app screens in a phone frame at phone width, motion by easing, no stock
  footage, burned-in captions plus a VTT file.
- **Delivery**: 1920x1080 at 30 fps, H.264, AAC 48 kHz stereo at 192 kbps,
  -14 LUFS integrated, -1 dBTP, speech alone at -16 LUFS, a bed at or below
  -28 LUFS and ducked under speech, or no bed.
- **Disclosure** on screen and in the provenance file: synthetic voice, made by AI
  agents, test tokens only. No cloned voice, no real person depicted.
- **Say "we are AI agents" and nothing about the operator** in any video,
  channel text or video description (operator direction, November 3). No "one
  human", no "under human direction": an operator behind agents is obvious and
  does not need saying.

## The pipeline (`tools/media/`, this repository)

```bash
python3 tools/media/make.py tools/media/spec.json --out build/omnequa-try-30s
```

| Step | File | What it does |
| --- | --- | --- |
| Spec | `spec.json` | Script per segment, captions, scene type, screens, voice, rate, music level, disclosure |
| Narration | `tts.py` | One clip per segment with word timings; trims silence; writes `timeline.json` |
| Frames | `scene.html`, `render.py` | Playwright seeks the page to each frame time and screenshots it; ffmpeg encodes |
| Bed | `music.py` | Original ambient pad, low-passed, no samples; optional (`--no-music`) |
| Mix and master | `make.py` | Levels speech, ducks the bed, masters to -14 LUFS / -1 dBTP, muxes, writes VTT and provenance |
| Measured QA | `qa.py` | Duration, codec, loudness, true peak, black frames, captions; exit 1 on failure |

Engine ladder for narration, best available first:

1. A premium engine whose key is in the environment (ElevenLabs, Cartesia or the
   OpenAI speech API; the operator queue holds the request). Add it to `tts.py`
   behind the same interface; the rest of the pipeline is unchanged.
2. Microsoft neural voices through `edge-tts` (default now). It needs no key. In
   the cloud container it must go through the HTTPS proxy with the CA bundle,
   which `tts.py` sets; the service drops some first attempts, so it retries.
3. Not for published work: small open models on a CPU (Kokoro-82M was episode 2),
   synthesized jingles, 64 kbps mono.

Reachability in the cloud container, probed November 3: the edge-tts endpoint,
`api.cartesia.ai`, `api.replicate.com`, `api.fal.ai` and `huggingface.co` answer;
`api.openai.com`, `api.elevenlabs.io`, `api.runwayml.com`, `api.heygen.com` and
`api.d-id.com` do not. Any of them needs an account and a key the team does not
hold, so they are operator queue items, optional.

## Gates

| Gate | Who | What | Written where |
| --- | --- | --- | --- |
| G0 Audition | Operator | Before a series starts, listen to 20 second samples of three voices and pick one; a voice is never chosen by an agent alone | `spec.json` (`voice`) and the provenance file |
| G1 Measured QA | Producing agent | `qa.py` passes; the contact sheet of eight frames shows no overlap, clipping or illegible text (agents can see images, so this is checked, not assumed) | `build/<slug>/qa.json` |
| G2 Claims | Claude | Every spoken figure or claim matches the public record; VERIFY rows where the vision rules require them | VERIFY.md in the vision repository |
| G3 Human review | Operator | Watches the cut; one round of notes; "approve" in writing. Required for the first three pieces per format, then spot checks | The PR or board comment that carries the approval |
| G4 Publication | Claude | Post with `video:` metadata, VTT and provenance beside the file; companions as the distribution rule requires | Vision repository |

No agent on the team can hear audio. Until a measured speech-quality judge is
added (a bounded task: run a public non-intrusive MOS predictor over each clip
and refuse below a threshold), perceptual judgment is the operator's, and the
team does not describe a production as good, natural or professional in any
record; it reports the measurements and the approval status.

## What this does not do

- It does not generate footage or avatars. Veo, Sora, Kling, HeyGen and
  Synthesia need accounts and are not needed for an app explainer; they stay out
  until a piece needs b-roll and the operator opens an account.
- It does not revive the two-voice episode format or its scheduler. The audio
  action `action:daily-audio-discussion-post` carries the learning; a new
  episode is produced only on the standard above, with a dialogue-trained engine
  and a passed audition.
- It does not change publication authority, holds, disclosure or claims rules.

## Branding

Every piece uses the Omnequa identity, not the blog's illustration palette:
`tools/media/brand.json` carries the tokens from the omnequa.org theme (navy
`#103747`, teal `#007d88`, aqua rules, pale teal `#edf7f8`, white; Georgia for
headlines, Arial/Helvetica for everything else; eyebrows uppercase in teal). The
approved logo (`tools/media/assets/brand/omnequa-logo.png`) appears complete and
unmodified on white: brand bar on light scenes, centered on the end card; never on
the navy band. The end card carries the name, the tagline "New technology. More
opportunity.", the URL in teal and the disclosure. The operator flagged the
branding of the first cut on November 3 (it used cream, amber and an invented
word mark); this section is the fix and `scene.html` implements it.

## Decisions on record

| Date | Gate | Decision |
| --- | --- | --- |
| 2026-11-03 | G0 | Narrator for the app and vision series: `en-US-AvaMultilingualNeural` (operator chose Ava over Andrew and Ryan from 15 second samples) |
| 2026-11-03 | G3 | The first cut "Omnequa: try a small loan" (Andrew voice, pre-brand) was judged publication quality by the operator; the published version is the same cut rebuilt with Ava and the brand fix |

## YouTube channel

The operator asked on November 3 whether the team can run a YouTube channel
with these pieces autonomously. Production, captions, metadata, the measured QA
and the journal post run without the operator. Upload needs the channel's own
Google account, which only the operator can create and consent for. Once done it
runs on its own. The plan is `tools/media/channel.json` (one piece a week, formats,
gates, measures, stop rule); the uploader is `tools/media/youtube_upload.py`.

Operator setup, once (about twenty minutes), in the operator queue:

1. Create the channel on a Google account the project controls (name Omnequa,
   avatar the approved logo, about text from `channel.json`).
2. In Google Cloud: a project, enable the YouTube Data API v3, create an OAuth
   client of type Desktop app, add the channel's account as a test user.
3. Consent once for the scope `https://www.googleapis.com/auth/youtube.upload`
   (and `youtube.force-ssl` for captions) and keep the refresh token.
4. Put `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` and `YOUTUBE_REFRESH_TOKEN`
   in the cloud environment's secrets. The hosts `www.googleapis.com` and
   `oauth2.googleapis.com` already answer from the container.

Until Google verifies the OAuth app, every API upload is locked to private;
the operator makes each one public in YouTube Studio (one click), or submits the
app for verification so the team can publish directly. The uploader marks every
video as synthetic media, category Education, with the VTT as English captions.
