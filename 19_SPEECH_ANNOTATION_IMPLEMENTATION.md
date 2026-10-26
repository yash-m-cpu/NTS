# 19 — Speech & Speaker Annotation for the OpenCV Annotated-Video Pipeline

**Status:** Design + implementation blueprint
**Extends:** Phase 11 `video_annotation_worker.py` (OpenCV overlay renderer)
**Depends on (data produced by):** docs 12 (attribution), 13 (speech analysis), 14 (listener analysis), 16 (schema), 17 (pipeline)

> **Provenance note on this document.** Only `project_history_summary.md` was available when this was written. Docs 11–18 and the repository itself were **not** inspected. Every table/column/function name below marked *(proposed)* is a contract this renderer needs; reconcile it against doc 16 and the real schema in the Phase 1 audit of doc 20 before coding. Names of existing code (`video_annotation_worker.py`, `feature_extractions`, `participant_tracks`) come from the history summary. Their internal signatures are unverified.

---

## 1. Goals and non-goals

**Goals**

1. For every rendered frame, show who is speaking (by `participant_track_id`), how confident that attribution is, and what they are saying.
2. Show speech activity, pitch and (when meaningful) speaking rate for the speaker.
3. Optionally show listener behavior labels, worded as observations or hedged inferences, never as traits.
4. Handle overlap, unknown speaker, off-screen speaker and silence explicitly.
5. Zero CV re-inference, zero STT re-inference. The renderer is a pure consumer of stored rows.
6. Keep render time close to the existing overlay-only render (target: ≤ 1.25× current wall-clock, see §12).

**Non-goals**

- No new models. No writing to feature tables from the renderer.
- No psychological or trait labels ("bored", "disengaged", "dominant person"). See §7.4.

---

## 2. Design principles

| Principle | Consequence in the renderer |
|---|---|
| **Read-only consumer** | The renderer only `SELECT`s. All thresholds that define *what happened* live upstream; the renderer only owns *how it is displayed* (hold times, tiers, layout). |
| **Observed vs inferred is visible** | Directly measured values (pitch, VAD activity, transcript) use a **solid** border; inferred values (speaker attribution, listener states) use a **dashed** border. |
| **Never claim more than the evidence** | Attribution below a confidence floor is rendered as *unknown*, not as a weak guess. |
| **Color is never the only signal** | Every state has a text label and a border style in addition to color (colorblind-safe palette). |
| **Deterministic render** | Same inputs + same `renderer_version` + same config ⇒ byte-identical frame overlays. Enables caching by input hash. |
| **Provenance sidecar** | Each render emits a manifest tying overlays back to source row ids and pipeline run ids. |

---

## 3. Inputs (database contracts)

### 3.1 Existing (from history summary — verify)

| Data | Table (existing) | Renderer needs |
|---|---|---|
| Participant tracks | `participant_tracks` | `id`, `meeting_id`, display label (`P1`…) |
| Per-frame CV features | `feature_extractions` | bbox, body keypoints, head yaw/pitch/roll, gaze bearing, emotion — already loaded by the current annotation worker. **Reuse its loader unchanged.** |
| Media | `media_assets` | source video key, fps, duration, width, height |

### 3.2 New speech-side tables consumed *(proposed — align with doc 16)*

```
pipeline_runs        (id, meeting_id, stage, params_hash, code_version, status, finished_at)

speech_segments      (id, meeting_id, run_id,
                      start_ms, end_ms,               -- canonical timeline, video clock
                      text, language, asr_avg_logprob, no_speech_prob,
                      diar_cluster_id,                -- nullable
                      participant_track_id,           -- nullable  => unknown speaker
                      attribution_confidence,         -- 0..1 (combined, calibrated)
                      attribution_method,             -- e.g. 'lip_vad_corr_v1'
                      alt_track_id, alt_confidence,   -- runner-up, nullable
                      is_overlap,                     -- bool, computed upstream
                      words_per_min,                  -- nullable, segment-level
                      words_json)                     -- [{w, s_ms, e_ms, p}] nullable

track_speech_activity(meeting_id, run_id, participant_track_id, t_ms, activity,  -- 0..1
                      lip_activity, vad_prob)          -- 10 Hz grid

prosody_windows      (meeting_id, run_id, participant_track_id, t_ms,            -- 100 ms hop
                      f0_hz, voiced, rms_db)           -- f0_hz NULL if unvoiced/overlap-excluded

listener_states      (id, meeting_id, run_id, participant_track_id,
                      start_ms, end_ms,
                      state,                           -- SPEAKER_ORIENTED | LOOKING_AWAY |
                                                       -- POSSIBLE_NOTE_TAKING | POSSIBLE_DISTRACTION
                      target_track_id,                 -- speaker being oriented toward, nullable
                      confidence,                      -- 0..1
                      gaze_on_target_pct,              -- trailing-window value, nullable
                      evidence_json)
```

`listener_states` and `speech_segments.participant_track_id` are **inferences**. `prosody_windows`, `track_speech_activity`, and `words_json` are **measurements**. This split drives border style (§7.1).

### 3.3 Timeline alignment fields

```
media_assets.video_start_offset_ms   -- container start_time of video stream (ffprobe)
media_assets.audio_start_offset_ms   -- container start_time of audio stream
media_assets.av_offset_ms            -- (proposed) audio_start - video_start, plus any measured drift correction
```

All speech tables are stored on the **video clock in integer milliseconds** (the upstream audio phase applies `av_offset_ms` once). The renderer must not re-apply offsets. It verifies `run_id` metadata records the offset it assumed (§4.3).

---

## 4. Timestamp alignment

### 4.1 Frame → time

Do **not** use `frame_idx / fps` for variable-frame-rate (phone/Zoom) sources.

```
t_ms(frame) = round(pts_seconds * 1000)          # container PTS, from cv2.CAP_PROP_POS_MSEC
                                                  # fallback: frame_idx * 1000 / fps for CFR
```

`cv2.VideoCapture.get(cv2.CAP_PROP_POS_MSEC)` returns the PTS of the frame just decoded. Read it **after** `cap.read()`. Verify at start: probe with `ffprobe -select_streams v -show_entries frame=pts_time` for the first 200 frames; if PTS deltas vary > 5 % of the median, set `vfr=True` and always use PTS. If `cv2` returns 0/monotonic-broken values for a codec, fall back to an ffprobe-generated PTS array (one pass, cached per media asset).

### 4.2 Time → tick grid

Overlay state is resolved on a **100 ms tick grid**, not per frame:

```
tick(t_ms) = t_ms // 100            # state sampled at tick center (tick*100 + 50)
```

Rationale: speech/listener data is inherently ≤ 10 Hz; 30 fps video has 3 frames/tick; state resolution runs ~10× less often, and the hold/hysteresis rules (§7.3) become simple integer arithmetic. Boundary error is ≤ 50 ms, below the alignment error of Whisper timestamps.

### 4.3 Alignment guards (fail loudly)

At render start:

1. `abs(audio_end_ms - video_end_ms) > 1000` → log `WARN av_duration_mismatch` and record in manifest.
2. `pipeline_runs.params` for the attribution run must include `av_offset_ms`. If it differs from the current `media_assets.av_offset_ms`, **abort** with `STALE_ALIGNMENT` (the speech rows were computed against another offset). The API layer then triggers re-attribution, not the renderer.
3. Clamp all segment times to `[0, video_duration_ms]`.

---

## 5. Database queries

All queries run **once per render**, results go to NumPy arrays / dataclass lists in memory. **No per-frame queries.**

```sql
-- 5.1 segments (typically 10^2–10^4 rows for a meeting)
SELECT id, start_ms, end_ms, text, participant_track_id, attribution_confidence,
       alt_track_id, alt_confidence, diar_cluster_id, is_overlap,
       words_per_min, words_json, attribution_method
FROM   speech_segments
WHERE  meeting_id = :meeting_id AND run_id = :attr_run_id
  AND  end_ms > 0 AND start_ms < :duration_ms
ORDER  BY start_ms, id;

-- 5.2 speech activity (10 Hz; 1 h × 4 tracks ≈ 144k rows)
SELECT participant_track_id, t_ms, activity
FROM   track_speech_activity
WHERE  meeting_id = :meeting_id AND run_id = :activity_run_id
ORDER  BY participant_track_id, t_ms;

-- 5.3 pitch (100 ms hop; 1 h × 4 tracks ≈ 144k rows)
SELECT participant_track_id, t_ms, f0_hz, voiced
FROM   prosody_windows
WHERE  meeting_id = :meeting_id AND run_id = :prosody_run_id
ORDER  BY participant_track_id, t_ms;

-- 5.4 listener states (interval rows, small)
SELECT participant_track_id, start_ms, end_ms, state, target_track_id,
       confidence, gaze_on_target_pct
FROM   listener_states
WHERE  meeting_id = :meeting_id AND run_id = :listener_run_id
ORDER  BY participant_track_id, start_ms;

-- 5.5 latest successful run ids per stage (resolved once)
SELECT DISTINCT ON (stage) stage, id, params_hash, code_version
FROM   pipeline_runs
WHERE  meeting_id = :meeting_id AND status = 'succeeded'
  AND  stage IN ('speaker_attribution','speech_activity','prosody','listener_analysis')
ORDER  BY stage, finished_at DESC;
```

Required indexes *(proposed)*: `speech_segments (meeting_id, run_id, start_ms)`, `track_speech_activity (meeting_id, run_id, participant_track_id, t_ms)`, `prosody_windows` same shape, `listener_states (meeting_id, run_id, participant_track_id, start_ms)`.

Loading uses SQLAlchemy async with `stream_scalars`/`yield_per(10_000)` and `np.fromiter` into preallocated arrays to keep peak memory bounded. Existing CV feature loading remains as-is.

---

## 6. Frame-level logic

### 6.1 Precompute pass (once, before decoding)

Build a `TickTimeline` = list of `TickState`, one per 100 ms. Cost is O(total speech ticks + tracks × ticks).

```text
function build_tick_timeline(segments, activity, pitch, listener, tracks, duration_ms, cfg):
    n_ticks = duration_ms // 100 + 1
    seg_at_tick = [[] for _ in range(n_ticks)]

    # 1) paint segments onto ticks (segments are already sorted)
    for seg in segments:
        first = ceil((seg.start_ms - 50) / 100)         # tick centers inside [start, end)
        last  = floor((seg.end_ms   - 50) / 100)
        for k in range(max(first,0), min(last, n_ticks-1) + 1):
            seg_at_tick[k].append(seg.idx)

    timeline = []
    for k in range(n_ticks):
        t = k*100 + 50
        active = [segments[i] for i in seg_at_tick[k]]
        timeline.append(resolve_tick(t, active, ...))   # §6.2
    apply_hold_and_hysteresis(timeline, cfg)            # §7.3
    return timeline
```

### 6.2 Per-tick resolution

```text
function resolve_tick(t, active_segments, ...):
    tick = TickState(t)
    if no active_segments:
        tick.mode = NO_SPEECH
        return tick

    # -- Step A: classify each active segment's attribution -------------
    for seg in active_segments:
        c = seg.attribution_confidence
        if seg.participant_track_id is None or c < cfg.conf_floor:      # default 0.35
            tick.unknown_speech.append(seg)                              # §9.3
        elif seg.alt_track_id is not None and (c - seg.alt_confidence) < cfg.margin_min:   # 0.10
            tick.add_speaker(seg.participant_track_id, seg, kind=CANDIDATE)
            tick.add_speaker(seg.alt_track_id,        seg, kind=CANDIDATE, conf=seg.alt_confidence)
        elif c >= cfg.conf_high:                                         # default 0.75
            tick.add_speaker(seg.participant_track_id, seg, kind=SPEAKING)
        else:
            tick.add_speaker(seg.participant_track_id, seg, kind=SPEAKING_LOW_CONF)

    # -- Step B: dedupe per track (keep highest confidence) -------------
    # -- Step C: overlap flag -------------------------------------------
    tick.is_overlap = len(distinct speaker tracks) >= 2 or any(seg.is_overlap)

    # -- Step D: measurements for each speaker track --------------------
    for track in tick.speakers:
        track.activity = sample_activity(track, t)             # 0..1 or None
        track.pitch    = sample_pitch(track, t, window=300ms)  # median of voiced f0, or None
        track.rate     = seg.words_per_min if rate_is_meaningful(seg) else None   # §8.4

    # -- Step E: listeners (only when at least one confident speaker) ----
    speaker_ids = {s.track_id for s in tick.speakers if s.kind in (SPEAKING, SPEAKING_LOW_CONF)}
    for track in all_tracks not in speaker_ids:
        ls = listener_state_at(track, t)
        if ls is None or ls.confidence < cfg.listener_conf_floor:        # default 0.50
            continue
        if ls.state == SPEAKER_ORIENTED and ls.target_track_id not in speaker_ids:
            continue                # oriented toward someone who isn't the current speaker
        if ls.state == SPEAKER_ORIENTED and tick.is_overlap and len(speaker_ids) > 1 and ls.target_track_id is None:
            continue                # ambiguous target under overlap
        tick.listeners[track] = ls

    # -- Step F: caption lines -------------------------------------------
    tick.captions = build_caption_lines(active_segments, t)      # §10
    return tick
```

`sample_pitch`: median of `f0_hz` over the trailing 300 ms where `voiced` is true; returns `None` if fewer than 2 voiced windows (→ render `Pitch: —`, never 0).

### 6.3 Per-frame render loop

```text
open capture, open writer (§12)
for each decoded frame:
    t_ms = pts_ms(frame)
    tick = timeline[min(t_ms // 100, last)]
    boxes = existing_cv_overlay(frame, cv_features_at(frame))        # REUSED, unchanged
    if speech_overlay_enabled:
        speech_renderer.draw(frame, tick, boxes_by_track, t_ms)
    writer.write(frame)
```

`boxes_by_track` comes from the existing worker's per-frame bbox lookup; the speech renderer never reads the CV tables directly.

---

## 7. Status semantics, colors, and language

### 7.1 State table

Palette: Okabe–Ito (colorblind-safe). Shown as RGB; convert to BGR for OpenCV or blend through Pillow.

| State | Label text | Color (RGB) | Border | Epistemic class | Shown when |
|---|---|---|---|---|---|
| Speaking (high conf) | `SPEAKING` | green `#009E73` | solid 3 px | attribution = **inferred**, values = observed | conf ≥ 0.75 |
| Speaking (medium conf) | `SPEAKING?` | amber `#E69F00` | dashed 3 px | inferred | 0.35 ≤ conf < 0.75 |
| Candidate | `SPEAKER CANDIDATE` | amber `#E69F00` | dotted | inferred | top-2 margin < 0.10 |
| Overlap badge | `OVERLAP` | vermillion `#D55E00` | (badge on caption + speaker panels) | observed (multiple active segments) | ≥ 2 speaker tracks active |
| Unknown speaker | `SPEECH · SPEAKER UNKNOWN` | grey `#9AA0A6` | solid, banner | observed (speech present) | speech active, attribution failed |
| Off-screen speaker | `Pn · OFF-SCREEN` | grey `#9AA0A6` | dashed | inferred | speaker track has no bbox for > 500 ms |
| Speaker-oriented | `SPEAKER-ORIENTED` | blue `#0072B2` | dashed | inferred | listener state |
| Looking away | `LOOKING AWAY` | sky `#56B4E9` | dashed | inferred | listener state |
| Possible note-taking | `POSSIBLE NOTE-TAKING` | purple-pink `#CC79A7` | dashed | inferred | listener state |
| Possible distraction | `POSSIBLE DISTRACTION` | yellow `#F0E442` (dark text) | dashed | inferred | listener state |
| No data | `NO DATA` | dim grey | none | — | listener conf < floor: **omit panel**, draw plain CV box |

The existing CV bounding box color is kept; the speech layer adds an **outer** 3 px status outline plus the panel. The speech color never replaces the CV box color.

### 7.2 Legend

Render a compact legend in the top-right for the first 5 s of the video (fade out) and burn into a sidecar `legend.png`. Legend includes: solid = measured, dashed = inferred.

### 7.3 Temporal stability (anti-flicker)

Applied on the tick timeline, after resolution:

| Rule | Default | Effect |
|---|---|---|
| Speaker hold-over | 300 ms | `SPEAKING` persists this long after segment end (mouth close / trailing silence) |
| Min show time | 500 ms | A speaker panel never shows for < 500 ms unless the underlying segment is shorter, in which case it is shown for the full segment + hold |
| Listener min duration | 1000 ms | A listener state shorter than this is not drawn (already enforced upstream; renderer re-enforces after joins) |
| Listener hold across gaps | 400 ms | Same state on same track separated by a gap ≤ 400 ms is bridged |
| Pitch/activity display update | 5 Hz | Displayed numbers change at most 5×/s to stay readable |
| Confidence tier hysteresis | ±0.03 | Avoids toggling `SPEAKING` ↔ `SPEAKING?` around 0.75 |

### 7.4 Language rules (hard)

Allowed vocabulary is a closed set:
`SPEAKING`, `SPEAKING?`, `SPEAKER CANDIDATE`, `SPEAKER UNKNOWN`, `OFF-SCREEN`, `OVERLAP`, `SPEAKER-ORIENTED`, `LOOKING AWAY`, `POSSIBLE NOTE-TAKING`, `POSSIBLE DISTRACTION`.

Forbidden in any overlay, caption, or manifest label: *bored, disengaged, rude, dominant, shy, nervous, angry, lying, uninterested, attentive, confused*, and any personality/trait term. Emotion overlays from Phase 11 are unchanged, but are not merged into speech/listener panels.

Enforcement: `tests/annotation/test_label_lint.py` scans `style.py` label constants against a denylist, and the renderer only accepts labels from an `Enum`, so a free-text label cannot reach `putText`.

`POSSIBLE …` labels mean "the recorded head/gaze/pose signals are consistent with X". They are not statements about what the person was thinking or doing.

---

## 8. Overlay design

### 8.1 Speaker panel

```
┌─────────────────────┐
│ P2            ●●●●○ │   ← track label, confidence bar (5 segments)
│ SPEAKING            │   ← state label (color-filled header)
│ Confidence: 0.91    │
│ Pitch: 184 Hz       │
│ Activity: ▮▮▮▮▯     │
│ Rate: 152 wpm       │   ← only when meaningful (§8.4)
└─────────────────────┘
```

Rows drop from the bottom when data is missing (never show `0`/`NaN`):

| Missing | Rendering |
|---|---|
| pitch unvoiced / overlap-excluded | `Pitch: —` |
| activity absent | row omitted |
| rate not meaningful | row omitted |

### 8.2 Listener panel

```
┌─────────────────────┐
│ P3                  │
│ SPEAKER-ORIENTED    │
│ Gaze: 82%           │   ← gaze_on_target_pct (trailing 3 s), "Gaze: n/a" if window under-filled
└─────────────────────┘
```

Additional rows only when present in `evidence_json`: `Head: down 24°` for POSSIBLE NOTE-TAKING; `Off-target: 4.2 s` for LOOKING AWAY / POSSIBLE DISTRACTION. Numbers are the measurements the state was derived from. That is what makes the inference inspectable on the frame itself.

`Gaze: 82%` definition (must appear in legend/manifest): share of frames in the trailing 3 s window, with valid gaze data, whose gaze bearing pointed within tolerance of the current speaker's bbox. Window must contain ≥ 15 valid frames or the field shows `n/a`.

### 8.3 Placement and layout

1. **Anchor:** panel top-left at `(bbox.x, bbox.y - panel_h - 6)`; if not enough room above, place below the bbox; clamp into frame with 8 px margin.
2. **Scale:** `s = frame_height / 720`, clamped to [0.6, 2.0]. Font size, padding, and border thickness multiply by `s`.
3. **Small faces:** if `bbox.w < 0.08 * frame_w`, use **compact** mode (label + state only, no numeric rows).
4. **Collision resolution:** sort panels by anchor y; if a panel intersects a previously placed one, shift down by `panel_h + 4`; after 3 shifts, move to the **side gutter** (right margin stack) with a leader line to the bbox.
5. **Speaker priority:** speaker panels are placed first, listener panels after. Listener panels are dropped first when space is exhausted (log `listener_panels_suppressed` count in manifest).

### 8.4 Speaking rate — when displayed

`rate_is_meaningful(seg)` is true only if all hold:

- `seg.words_per_min is not None`
- segment duration ≥ 2.0 s
- word count ≥ 6
- segment is **not** flagged `is_overlap` (overlap corrupts word timing)
- `asr_avg_logprob ≥ -1.0` (skip very low-quality ASR)

The value is a **segment average**, labeled `Rate: 152 wpm (seg)` in the manifest and shown as `Rate: 152 wpm`. Because the render is offline, the segment average is available from the segment's first frame. That is acceptable, but the legend states it is a segment average, not instantaneous.

### 8.5 Confidence rendering

- Number: `attribution_confidence` to 2 decimals. Label is `Confidence` in the panel. This is **speaker-attribution confidence**, *not* ASR confidence. ASR confidence is never shown as the same word.
- Bar: 5 segments filled `round(conf * 5)`.
- Tiers: `≥ 0.75` solid / `0.35–0.75` dashed + `SPEAKING?` / `< 0.35` treated as unknown.
- Thresholds are config (`SpeechOverlayConfig`) and echoed into the manifest.

---

## 9. Edge cases

### 9.1 Multiple simultaneous speakers

- Each attributed track gets its own speaker panel.
- `OVERLAP` badge appears on the caption bar and beside each speaker's state label.
- Caption bar shows up to **2** speaker lines (highest confidence first), then `+N more`.
- Listener `SPEAKER-ORIENTED` is only shown when `target_track_id` is one of the active speakers; otherwise omitted rather than guessed.
- Pitch for a speaker in an overlap tick is drawn only if `prosody_windows.f0_hz` is non-null there. Upstream excludes overlap windows from pitch by default. Expect `Pitch: —` during overlap.

### 9.2 Soft attribution

If the top-2 margin is < 0.10 (`alt_confidence` close to `attribution_confidence`), draw **both** tracks as `SPEAKER CANDIDATE` with their own confidence values. No `SPEAKING` label is drawn for either.

### 9.3 Unknown speaker

Speech is active (segment exists) but `participant_track_id IS NULL` or conf < floor:

- Top-center banner: `SPEECH · SPEAKER UNKNOWN` (grey). If `diar_cluster_id` exists: append `(cluster S2)`.
- Transcript still shows in the caption bar, prefixed `?:` in grey.
- **No face gets a SPEAKING label.** The candidate track is recorded in the manifest only, never on screen.
- No listener `SPEAKER-ORIENTED` is drawn because there is no confident target.

### 9.4 Speaker off-screen / track lost

Speaker `participant_track_id` is set but no bbox exists for that track in this frame:

- Reuse the last known bbox for up to 500 ms (interpolation of the position only, draw with dashed outline).
- Beyond 500 ms: draw a chip in the side gutter `P4 · OFF-SCREEN · SPEAKING` with panel content, no leader line.

### 9.5 No speech

- No speaker or listener panels are drawn (listener states are only meaningful relative to a speaker).
- Plain CV overlay from Phase 11 continues unchanged.
- A small muted pill `NO SPEECH` appears bottom-left (togglable via `show_no_speech_pill`, default on) with a running silence duration once silence exceeds 2 s: `NO SPEECH · 3.4 s`.

### 9.6 Silence-with-lips-moving / speech-with-no-lips

Not resolved in the renderer. These are upstream attribution outcomes (low confidence or unknown) and render through the tiers above.

### 9.7 Missing upstream data

| Missing | Behavior |
|---|---|
| No `speech_segments` for the meeting | Speech overlay auto-disabled; job result carries `speech_overlay=skipped_no_data`; existing render runs |
| No `prosody_windows` | Panel omits Pitch row |
| No `listener_states` | Listener panels omitted |
| `words_json` null | Caption falls back to whole-segment text (no word reveal) |

---

## 10. Transcript rendering

### 10.1 Layout

- Bottom caption band, height `≈ 0.16 * H` max, drawn as a semi-transparent (α 0.55) black rounded rectangle, 5 % horizontal margin.
- Each line: `[P2] text…` where `[P2]` is colored by that track's status color.
- Max 2 speaker lines, each wrapped to at most 2 text lines (ellipsis `…` if longer, using the *end* of the text nearest the current word so the currently spoken words stay visible).

### 10.2 Word reveal

If `words_json` exists:

- Words with `s_ms ≤ t_ms` render bright white.
- Upcoming words (`s_ms > t_ms`, up to 6 words ahead) render dim grey.
- Words further ahead are not shown (avoids reading ahead of the audio).

Else: whole segment text, bright.

### 10.3 Timing

| Item | Value |
|---|---|
| Pre-roll | 0 ms (caption appears at segment start) |
| Linger after segment end | 300 ms |
| Min on-screen time | 700 ms |
| Line change | On segment change only, never mid-segment |

### 10.4 Text rendering engine

`cv2.putText` (Hershey) only supports ASCII. Transcripts may contain Unicode/non-Latin scripts, so all text goes through a **Pillow-backed `TextRenderer`** with per-string sprite cache (§12) and a bundled font (Noto Sans + Noto Sans fallback for the detected `language`). Panels/captions are rendered to RGBA sprites once and alpha-blended into the frame ROI with NumPy. `cv2` is used only for boxes, dashed lines, and blending.

Transcript text is drawn as recorded. The renderer does not translate, correct, or summarize.

---

## 11. Code structure (concrete)

```
backend/app/annotation/speech_overlay/
├── __init__.py
├── config.py          # SpeechOverlayConfig (thresholds, holds, toggles)
├── models.py          # dataclasses: Segment, Word, ListenerState, TrackOverlay, TickState
├── loader.py          # async DB → in-memory arrays (queries §5)
├── alignment.py       # PTS reader, av offset guards, tick helpers
├── timeline.py        # build_tick_timeline, resolve_tick, hold/hysteresis
├── style.py           # Enum labels, palette, dash patterns, label denylist
├── text_cache.py      # Pillow TextRenderer + LRU sprite cache
├── layout.py          # panel sizing, anchor, collision resolution
├── renderer.py        # SpeechOverlayRenderer.draw(frame, tick, boxes_by_track, t_ms)
└── manifest.py        # provenance sidecar writer

backend/app/workers/video_annotation_worker.py   # MODIFIED (small): wire provider in
tests/annotation/                                # §14
```

### 11.1 `models.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Kind(str, Enum):
    SPEAKING = "SPEAKING"
    SPEAKING_LOW = "SPEAKING?"
    CANDIDATE = "SPEAKER CANDIDATE"
    OFFSCREEN = "OFF-SCREEN"
    ORIENTED = "SPEAKER-ORIENTED"
    LOOKING_AWAY = "LOOKING AWAY"
    NOTE_TAKING = "POSSIBLE NOTE-TAKING"
    DISTRACTION = "POSSIBLE DISTRACTION"

@dataclass(slots=True)
class Word:
    text: str
    s_ms: int
    e_ms: int

@dataclass(slots=True)
class Segment:
    idx: int
    id: int
    start_ms: int
    end_ms: int
    text: str
    track_id: Optional[int]
    conf: float
    alt_track_id: Optional[int]
    alt_conf: Optional[float]
    cluster_id: Optional[str]
    is_overlap: bool
    wpm: Optional[float]
    asr_logprob: Optional[float]
    words: list[Word] = field(default_factory=list)

@dataclass(slots=True)
class ListenerState:
    track_id: int
    start_ms: int
    end_ms: int
    kind: Kind
    target_track_id: Optional[int]
    conf: float
    gaze_pct: Optional[float]
    extra: dict            # evidence rows for display, e.g. {"head_pitch_deg": 24}

@dataclass(slots=True)
class TrackOverlay:
    track_id: int
    kind: Kind
    conf: float
    segment_id: Optional[int]
    activity: Optional[float] = None
    pitch_hz: Optional[float] = None
    wpm: Optional[float] = None
    gaze_pct: Optional[float] = None
    extra: dict = field(default_factory=dict)

@dataclass(slots=True)
class CaptionLine:
    track_id: Optional[int]     # None => unknown speaker
    segment_id: int
    text_bright: str
    text_dim: str
    conf: float
    unknown: bool

@dataclass(slots=True)
class TickState:
    t_ms: int
    speakers: dict[int, TrackOverlay] = field(default_factory=dict)
    listeners: dict[int, TrackOverlay] = field(default_factory=dict)
    unknown_segments: list[Segment] = field(default_factory=list)
    captions: list[CaptionLine] = field(default_factory=list)
    is_overlap: bool = False
    silent_for_ms: int = 0
```

### 11.2 `config.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SpeechOverlayConfig:
    tick_ms: int = 100
    conf_high: float = 0.75
    conf_floor: float = 0.35
    margin_min: float = 0.10
    conf_hysteresis: float = 0.03
    listener_conf_floor: float = 0.50
    speaker_hold_ms: int = 300
    speaker_min_show_ms: int = 500
    listener_min_ms: int = 1000
    listener_bridge_ms: int = 400
    caption_linger_ms: int = 300
    caption_min_ms: int = 700
    caption_max_lines: int = 2
    offscreen_grace_ms: int = 500
    pitch_window_ms: int = 300
    number_update_hz: int = 5
    show_listeners: bool = True
    show_rate: bool = True
    show_no_speech_pill: bool = True
    compact_face_frac: float = 0.08
    renderer_version: str = "speech_overlay_v1"
```

### 11.3 `alignment.py` (PTS and tick helpers)

```python
import cv2

def frame_time_ms(cap: "cv2.VideoCapture", frame_idx: int, fps: float, vfr: bool) -> int:
    # Call AFTER cap.read(). POS_MSEC = PTS of the frame just decoded.
    if vfr:
        pos = cap.get(cv2.CAP_PROP_POS_MSEC)
        if pos and pos > 0:
            return int(round(pos))
    return int(round(frame_idx * 1000.0 / fps))

def tick_of(t_ms: int, tick_ms: int, n_ticks: int) -> int:
    k = t_ms // tick_ms
    return 0 if k < 0 else (n_ticks - 1 if k >= n_ticks else k)
```

### 11.4 `timeline.py`

```python
from __future__ import annotations
import math
import numpy as np
from .models import *
from .config import SpeechOverlayConfig

class SignalSeries:
    """Sorted (t_ms, value) arrays per track. O(log n) sample via searchsorted."""
    def __init__(self, t: np.ndarray, v: np.ndarray, voiced: np.ndarray | None = None):
        self.t, self.v, self.voiced = t, v, voiced

    def window_median_voiced(self, t_ms: int, win_ms: int) -> float | None:
        lo = np.searchsorted(self.t, t_ms - win_ms, side="left")
        hi = np.searchsorted(self.t, t_ms, side="right")
        if hi - lo < 2:
            return None
        vals = self.v[lo:hi]
        if self.voiced is not None:
            vals = vals[self.voiced[lo:hi]]
        vals = vals[~np.isnan(vals)]
        return float(np.median(vals)) if vals.size >= 2 else None

    def at(self, t_ms: int) -> float | None:
        i = np.searchsorted(self.t, t_ms, side="right") - 1
        return float(self.v[i]) if 0 <= i < len(self.t) and t_ms - self.t[i] <= 200 else None


def build_tick_timeline(segments: list[Segment],
                        activity: dict[int, SignalSeries],
                        pitch: dict[int, SignalSeries],
                        listener_by_track: dict[int, list[ListenerState]],
                        track_ids: list[int],
                        duration_ms: int,
                        cfg: SpeechOverlayConfig) -> list[TickState]:
    n = duration_ms // cfg.tick_ms + 1
    seg_at: list[list[int]] = [[] for _ in range(n)]
    for s in segments:
        first = max(0, math.ceil((s.start_ms - cfg.tick_ms / 2) / cfg.tick_ms))
        last = min(n - 1, math.floor((s.end_ms - cfg.tick_ms / 2) / cfg.tick_ms))
        for k in range(first, last + 1):
            seg_at[k].append(s.idx)

    ticks = [
        _resolve_tick(k * cfg.tick_ms + cfg.tick_ms // 2,
                      [segments[i] for i in seg_at[k]],
                      activity, pitch, listener_by_track, track_ids, cfg)
        for k in range(n)
    ]
    _apply_hold(ticks, cfg)
    _fill_silence_counter(ticks, cfg)
    return ticks


def _rate_ok(s: Segment) -> bool:
    return (s.wpm is not None and (s.end_ms - s.start_ms) >= 2000
            and len(s.words) >= 6 and not s.is_overlap
            and (s.asr_logprob is None or s.asr_logprob >= -1.0))


def _resolve_tick(t, active, activity, pitch, listeners, track_ids, cfg) -> TickState:
    tick = TickState(t_ms=t)
    if not active:
        return tick

    for s in active:
        c = s.conf
        if s.track_id is None or c < cfg.conf_floor:
            tick.unknown_segments.append(s)
            continue
        if s.alt_track_id is not None and s.alt_conf is not None and (c - s.alt_conf) < cfg.margin_min:
            _put(tick.speakers, TrackOverlay(s.track_id, Kind.CANDIDATE, c, s.id))
            _put(tick.speakers, TrackOverlay(s.alt_track_id, Kind.CANDIDATE, s.alt_conf, s.id))
            continue
        kind = Kind.SPEAKING if c >= cfg.conf_high else Kind.SPEAKING_LOW
        ov = TrackOverlay(s.track_id, kind, c, s.id, wpm=s.wpm if (cfg.show_rate and _rate_ok(s)) else None)
        _put(tick.speakers, ov)

    for tid, ov in tick.speakers.items():
        a = activity.get(tid)
        p = pitch.get(tid)
        ov.activity = a.at(t) if a else None
        ov.pitch_hz = p.window_median_voiced(t, cfg.pitch_window_ms) if p else None

    tick.is_overlap = len(tick.speakers) >= 2 or any(s.is_overlap for s in active)

    if cfg.show_listeners:
        confident = {tid for tid, o in tick.speakers.items() if o.kind in (Kind.SPEAKING, Kind.SPEAKING_LOW)}
        for tid in track_ids:
            if tid in tick.speakers:
                continue
            ls = _listener_at(listeners.get(tid, []), t)
            if ls is None or ls.conf < cfg.listener_conf_floor:
                continue
            if ls.kind == Kind.ORIENTED and ls.target_track_id not in confident:
                continue
            tick.listeners[tid] = TrackOverlay(tid, ls.kind, ls.conf, None,
                                               gaze_pct=ls.gaze_pct, extra=ls.extra)
    tick.captions = _captions(active, tick, t, cfg)
    return tick


def _put(d: dict, ov: TrackOverlay):
    cur = d.get(ov.track_id)
    if cur is None or ov.conf > cur.conf:
        d[ov.track_id] = ov


def _listener_at(rows: list[ListenerState], t: int):
    # rows sorted by start_ms; small lists -> linear/bisect both fine
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid].start_ms <= t: lo = mid + 1
        else: hi = mid
    i = lo - 1
    return rows[i] if i >= 0 and rows[i].end_ms > t else None
```

`_captions`, `_apply_hold`, and `_fill_silence_counter` implement §7.3 / §10.3. `_apply_hold` works on the tick array. For each track's speaker overlay it copies the overlay forward `speaker_hold_ms / tick_ms` ticks and extends any run shorter than `speaker_min_show_ms`. Held ticks are marked `extra["held"]=True` so the manifest distinguishes them from directly attributed ticks.

### 11.5 `text_cache.py`

```python
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class TextRenderer:
    def __init__(self, font_path: str, fallback_paths: list[str] | None = None):
        self.font_path, self.fallbacks = font_path, fallback_paths or []
        self._fonts: dict[int, ImageFont.FreeTypeFont] = {}

    def font(self, px: int):
        f = self._fonts.get(px)
        if f is None:
            f = self._fonts[px] = ImageFont.truetype(self.font_path, px)
        return f

    def measure(self, text: str, px: int) -> tuple[int, int]:
        l, t, r, b = self.font(px).getbbox(text)
        return r - l, b - t

    @lru_cache(maxsize=2048)
    def sprite(self, text: str, px: int, rgb: tuple, bg_rgba: tuple | None = None) -> np.ndarray:
        """Returns HxWx4 uint8 RGBA, cached by (text, px, colors)."""
        w, h = self.measure(text, px)
        im = Image.new("RGBA", (w + 8, h + 8), bg_rgba or (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4, 2), text, font=self.font(px), fill=rgb + (255,))
        return np.asarray(im)


def blend_rgba(frame_bgr: np.ndarray, sprite_rgba: np.ndarray, x: int, y: int, alpha_mul: float = 1.0):
    H, W = frame_bgr.shape[:2]
    h, w = sprite_rgba.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    sp = sprite_rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = (sp[..., 3:4].astype(np.float32) / 255.0) * alpha_mul
    roi = frame_bgr[y0:y1, x0:x1]
    roi[:] = (sp[..., 2::-1] * a + roi * (1 - a)).astype(np.uint8)   # RGB→BGR, ROI-only blend
```

### 11.6 `layout.py`

```python
from dataclasses import dataclass

@dataclass
class Rect: x: int; y: int; w: int; h: int
def intersects(a: Rect, b: Rect) -> bool:
    return not (a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y)

def place_panels(requests, frame_w, frame_h, scale):
    """
    requests: list[(track_id, panel_w, panel_h, bbox_xywh|None, priority)]
    returns:  dict[track_id, (Rect, needs_leader_line: bool)]
    priority: 0 = speaker, 1 = listener  (speakers placed first)
    """
    placed: list[Rect] = []
    out = {}
    gutter_x = frame_w - int(220 * scale) - 8
    gutter_y = 8
    for tid, pw, ph, bb, _ in sorted(requests, key=lambda r: (r[4], r[3][1] if r[3] else 1e9)):
        if bb is None:                                       # off-screen → gutter
            r = Rect(gutter_x, gutter_y, pw, ph); gutter_y += ph + 6
            out[tid] = (r, False); placed.append(r); continue
        bx, by, bw, bh = bb
        r = Rect(min(max(bx, 8), frame_w - pw - 8),
                 by - ph - 6 if by - ph - 6 >= 8 else by + bh + 6, pw, ph)
        for _ in range(3):
            hit = next((p for p in placed if intersects(r, p)), None)
            if hit is None: break
            r.y = hit.y + hit.h + 4
        else:
            r = Rect(gutter_x, gutter_y, pw, ph); gutter_y += ph + 6
            out[tid] = (r, True); placed.append(r); continue
        r.y = min(max(r.y, 8), frame_h - ph - 8)
        out[tid] = (r, False); placed.append(r)
    return out
```

### 11.7 `renderer.py`

```python
import cv2
import numpy as np
from .models import *
from .style import STYLE, dashed_rect
from .text_cache import TextRenderer, blend_rgba
from .layout import place_panels

class SpeechOverlayRenderer:
    def __init__(self, cfg, text: TextRenderer, frame_w: int, frame_h: int):
        self.cfg, self.text = cfg, text
        self.W, self.H = frame_w, frame_h
        self.s = min(max(frame_h / 720.0, 0.6), 2.0)
        self._panel_cache: dict[tuple, np.ndarray] = {}     # key -> RGBA sprite
        self._last_bbox: dict[int, tuple[int, tuple]] = {}  # track -> (t_ms, bbox)

    # ---- public --------------------------------------------------------
    def draw(self, frame: np.ndarray, tick: TickState, bboxes: dict[int, tuple], t_ms: int) -> None:
        for tid, bb in bboxes.items():
            self._last_bbox[tid] = (t_ms, bb)

        reqs, sprites = [], {}
        for group, prio in ((tick.speakers, 0), (tick.listeners, 1)):
            for tid, ov in group.items():
                bb = self._bbox_for(tid, bboxes, t_ms)
                compact = bb is not None and bb[2] < self.cfg.compact_face_frac * self.W
                sp = self._panel(ov, compact, offscreen=bb is None)
                sprites[tid] = (sp, ov, bb)
                reqs.append((tid, sp.shape[1], sp.shape[0], bb, prio))

        for tid, (rect, leader) in place_panels(reqs, self.W, self.H, self.s).items():
            sp, ov, bb = sprites[tid]
            if bb is not None:
                self._draw_outline(frame, bb, ov)
            blend_rgba(frame, sp, rect.x, rect.y)
            if leader and bb is not None:
                cv2.line(frame, (rect.x, rect.y + rect.h // 2),
                         (bb[0] + bb[2] // 2, bb[1]), STYLE.color_bgr(ov.kind), 1, cv2.LINE_AA)

        if tick.unknown_segments:
            self._draw_unknown_banner(frame, tick)
        self._draw_captions(frame, tick, t_ms)
        if not tick.speakers and not tick.unknown_segments and self.cfg.show_no_speech_pill:
            self._draw_no_speech(frame, tick)

    # ---- helpers -------------------------------------------------------
    def _bbox_for(self, tid, bboxes, t_ms):
        if tid in bboxes:
            return bboxes[tid]
        last = self._last_bbox.get(tid)
        if last and t_ms - last[0] <= self.cfg.offscreen_grace_ms:
            return last[1]
        return None

    def _panel(self, ov: TrackOverlay, compact: bool, offscreen: bool) -> np.ndarray:
        # quantize numbers so the sprite cache actually hits
        key = (ov.kind, round(ov.conf, 2), compact, offscreen, ov.track_id,
               None if ov.pitch_hz is None else int(round(ov.pitch_hz)),
               None if ov.activity is None else int(round(ov.activity * 5)),
               None if ov.wpm is None else int(round(ov.wpm)),
               None if ov.gaze_pct is None else int(round(ov.gaze_pct)),
               tuple(sorted(ov.extra.items())) if ov.extra else ())
        sp = self._panel_cache.get(key)
        if sp is None:
            sp = self._render_panel(ov, compact, offscreen)
            if len(self._panel_cache) > 1024:
                self._panel_cache.clear()
            self._panel_cache[key] = sp
        return sp

    def _render_panel(self, ov, compact, offscreen) -> np.ndarray:
        rows = [f"P{ov.track_id}" + ("  · OFF-SCREEN" if offscreen else ""), ov.kind.value]
        if not compact:
            if ov.kind in (Kind.SPEAKING, Kind.SPEAKING_LOW, Kind.CANDIDATE):
                rows.append(f"Confidence: {ov.conf:.2f}")
                rows.append("Pitch: " + (f"{ov.pitch_hz:.0f} Hz" if ov.pitch_hz else "—"))
                if ov.activity is not None:
                    n = int(round(ov.activity * 5)); rows.append("Activity: " + "▮" * n + "▯" * (5 - n))
                if ov.wpm:
                    rows.append(f"Rate: {ov.wpm:.0f} wpm")
            else:
                rows.append("Gaze: " + (f"{ov.gaze_pct:.0f}%" if ov.gaze_pct is not None else "n/a"))
                if "head_pitch_deg" in ov.extra: rows.append(f"Head: down {ov.extra['head_pitch_deg']:.0f}°")
                if "off_target_s" in ov.extra:   rows.append(f"Off-target: {ov.extra['off_target_s']:.1f} s")
        return STYLE.compose_panel(self.text, rows, ov.kind, self.s,
                                   dashed=ov.kind not in (Kind.SPEAKING,))

    def _draw_outline(self, frame, bb, ov):
        x, y, w, h = bb
        col = STYLE.color_bgr(ov.kind)
        if ov.kind == Kind.SPEAKING:
            cv2.rectangle(frame, (x - 3, y - 3), (x + w + 3, y + h + 3), col, max(2, int(3 * self.s)))
        else:
            dashed_rect(frame, (x - 3, y - 3, w + 6, h + 6), col, max(2, int(3 * self.s)))

    # _draw_unknown_banner / _draw_captions / _draw_no_speech follow §9.3, §10, §9.5
```

Three details in the sketch are intentional:

- **ROI-only alpha blend** (`blend_rgba`) instead of `cv2.addWeighted` on the whole frame.
- **Numbers quantized before cache lookup**: a panel sprite is re-rasterized only when a displayed value changes.
- **`_last_bbox`** state is the only per-frame mutable state in the renderer, so chunked parallel rendering (§12.4) resets it at chunk boundaries and uses a 500 ms warm-up read.

### 11.8 Integration into the existing worker (minimal diff)

```python
# video_annotation_worker.py  (MODIFIED — additive)
async def annotate_video(ctx, meeting_id: int, options: dict | None = None):
    opts = {"cv": True, "speech": True, **(options or {})}
    ...  # existing: load media asset, download video, load CV features (UNCHANGED)

    speech_renderer = timeline = None
    if opts["speech"]:
        data = await speech_loader.load(session, meeting_id)         # §5, returns None if no speech rows
        if data is not None:
            check_alignment(data, media_asset)                       # §4.3, may raise STALE_ALIGNMENT
            cfg = SpeechOverlayConfig()
            timeline = build_tick_timeline(data.segments, data.activity, data.pitch,
                                           data.listener, data.track_ids, duration_ms, cfg)
            speech_renderer = SpeechOverlayRenderer(cfg, text_renderer, W, H)

    for frame, frame_idx in frames:                                  # existing loop
        t_ms = frame_time_ms(cap, frame_idx, fps, vfr)
        boxes_by_track = draw_cv_overlays(frame, cv_features, frame_idx)   # existing, returns bboxes
        if speech_renderer:
            speech_renderer.draw(frame, timeline[tick_of(t_ms, cfg.tick_ms, len(timeline))],
                                 boxes_by_track, t_ms)
        sink.write(frame)
    ...  # existing: upload to MinIO, presigned GET (UNCHANGED)
    write_manifest(...)                                               # §13
```

The only requirement on the existing CV draw function is that it **returns the bbox per track for that frame** (`dict[track_id, (x, y, w, h)]`). If it does not today, add that return value. It is a read of data already computed and does not change drawing behavior.

---

## 12. Performance

### 12.1 Where time goes in a naive implementation

Decode → per-frame overlay → encode. The overlay is normally the cheapest part. The risks are (a) rasterizing text every frame, (b) full-frame blends, (c) a double encode, (d) per-frame DB or dict-of-dict work.

### 12.2 Measures

| Measure | Effect |
|---|---|
| State resolved on 100 ms ticks, precomputed once | Resolution cost ÷ 3 at 30 fps and moved out of the hot loop |
| All DB reads before decoding, into NumPy | Zero I/O in loop |
| Panel/caption sprites cached by quantized content | Typical frame = 0–3 cache hits, 0 rasterizations |
| ROI-only alpha blending | Touches ~1–3 % of pixels per frame |
| Numbers update at 5 Hz | Sprite churn ≤ 5/s/track |
| Single pass over the video: CV overlay + speech overlay in one loop | No extra decode/encode vs today |
| Reader / renderer / writer on separate threads with bounded queues (`maxsize=8`) | Overlaps decode + encode with drawing (cv2 releases the GIL in decode/encode/blend) |
| Pipe raw BGR frames to `ffmpeg -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -movflags +faststart` | Avoids the mp4v→transcode double encode; browser-playable output. If the existing worker already does this, leave it |
| Mux original audio (`-i original -map 0:v -map 1:a? -c:a copy`) | Speech captions are useless without sound. **Verify whether the current output has audio**, and add it if not |
| Render-cache by input hash | See §12.3 |

### 12.3 Render cache

```
input_hash = sha256(cv_run_id | attribution_run_id+params_hash | activity_run_id |
                    prosody_run_id | listener_run_id | SpeechOverlayConfig | renderer_version |
                    source_video_etag)
object key = annotated/{meeting_id}/{input_hash}.mp4
```

If the object exists, return a presigned URL immediately. Changing a threshold or upstream run produces a new object. The old one is garbage-collected by lifecycle rule (e.g., 14 days).

### 12.4 Optional: chunked parallel render

Split by GOP-aligned time ranges (`ffprobe` keyframes), render N chunks in N processes, concat with `-c copy`. Each chunk gets a copy of the `TickState` slice (fork-shared memory), and warms `_last_bbox` with the 500 ms preceding its start. Build only if a single-process render of a long meeting exceeds the target. Not part of the MVP.

### 12.5 Budgets (targets to validate, not measured)

| Metric | Target |
|---|---|
| Overlay time per frame (speech layer only) | < 1.5 ms at 720p, < 3 ms at 1080p |
| Total render wall-clock vs. current | ≤ 1.25× |
| Peak extra memory | < 300 MB for a 1 h, 4-track meeting |
| Timeline precompute | < 5 s for a 1 h meeting |

Measure with `py-spy` and a per-stage timer, and log `t_decode`, `t_cv_overlay`, `t_speech_overlay`, `t_encode` in the job result.

---

## 13. Provenance manifest and sidecars

Each render writes `annotated/{meeting_id}/{input_hash}.manifest.json` next to the MP4.

```json
{
  "renderer_version": "speech_overlay_v1",
  "input_hash": "…",
  "source": {"video_asset_id": 123, "duration_ms": 3600000, "fps": 29.97, "vfr": false,
             "av_offset_ms": -40},
  "runs": {"speaker_attribution": {"run_id": 88, "params_hash": "…", "code_version": "…"},
           "speech_activity": {...}, "prosody": {...}, "listener_analysis": {...}},
  "config": { "...SpeechOverlayConfig..." },
  "epistemics": {
    "measured": ["transcript_words", "pitch_hz", "speech_activity", "gaze_pct", "head_angles"],
    "inferred": ["speaker_attribution", "listener_state"]
  },
  "definitions": {
    "gaze_pct": "share of valid gaze frames in trailing 3 s pointing at current speaker bbox",
    "confidence": "speaker-attribution confidence (not ASR confidence)",
    "rate": "segment-average words/min, shown only when segment >=2 s and >=6 words"
  },
  "events": [
    {"t_start_ms": 84200, "t_end_ms": 87900, "track": 2, "kind": "SPEAKING",
     "conf": 0.91, "segment_id": 4711, "held_ms": 300}
  ],
  "suppressed": {"listener_panels": 12, "captions_truncated": 3, "unknown_speech_ms": 5400},
  "warnings": []
}
```

`events` is run-length encoded by `(track, kind, segment_id)`, so it stays small. It is consumed by the frontend (Phase 13) for seek-to-event and for "Who was speaking at 01:24.5?" style lookups from the same source of truth as the burned-in video.

**WebVTT sidecar:** `…/captions.vtt` with cues `<v P2>text</v>` (one per segment, attributed track as voice tag, `?` for unknown). The frontend `<video>` can use it as a toggleable text track, independent of the burned-in captions.

---

## 14. Testing

| Level | Test | Assertion |
|---|---|---|
| Unit | `tick` painting | Segment 1000–2000 ms paints ticks with centers 1050…1950 exactly |
| Unit | `resolve_tick` tiers | conf 0.91→SPEAKING, 0.6→SPEAKING?, 0.2→unknown, margin 0.05→2×CANDIDATE |
| Unit | overlap | 2 confident segments → `is_overlap`, 2 speakers, caption shows both |
| Unit | unknown | `track_id=None` → no speaker overlay, banner + `?:` caption |
| Unit | listener gating | ORIENTED with target not speaking → omitted |
| Unit | rate gating | short segment / overlap / few words → `wpm None` |
| Unit | pitch | unvoiced/NaN window → `None`, panel renders `—` |
| Unit | hold | segment end at t → speaker overlay persists `speaker_hold_ms` |
| Unit | label lint | no denylisted word in any label constant or manifest label |
| Unit | layout | overlapping bboxes → no panel overlaps; ≥ 4 close faces → gutter fallback |
| Alignment | VFR fixture | PTS-based time used; label appears at correct frame ±1 |
| Alignment | stale offset | mismatched `av_offset_ms` → `STALE_ALIGNMENT` |
| Golden | synthetic 10 s clip | Rendered frames at fixed timestamps match stored PNGs (SSIM ≥ 0.99) |
| Integration | end-to-end render | Manifest events == segments after hold; ffprobe shows h264 + audio |
| Integration | no speech rows | Render succeeds, speech layer skipped, status `skipped_no_data` |
| Regression | speech disabled | Output pixel-identical to current Phase 11 output |
| Perf | benchmark | Meets §12.5 budgets on a 10-minute 1080p fixture |

Synthetic fixture: a generated 2-track clip with hand-authored `speech_segments`, `prosody_windows`, `listener_states`, covering silence, single speaker, overlap, unknown speaker, off-screen speaker, and low-confidence transitions. No real meeting data needed in CI.

**Acceptance criteria**

1. At any timestamp, the frame's speaker label matches `SELECT … FROM speech_segments` for that time (± one tick, ± hold).
2. No overlay reaches the frame without going through a `Kind` enum label.
3. Unknown, overlapping, off-screen, and silent cases each render as specified in §9.
4. No CV or STT code path is invoked during a render (asserted by import-guard / monkeypatch in tests).
5. With `speech=false`, output is identical to the current pipeline.
6. Manifest reproduces the run ids, config, and per-event source segment ids.
7. Performance targets in §12.5 hold on the benchmark fixture.

---

## 15. Rollout

1. Add columns/tables (owned by doc 16 / Phase 2 of doc 20).
2. Ship `speech_overlay` package behind `options.speech` (default **off**).
3. Validate on the synthetic fixture, then one real meeting; compare a sample of frames against the transcript by hand.
4. Default on once the upstream attribution has an acceptance report.
5. Add "Annotated video (speech)" toggle to the frontend `MeetingAnalysis` page (Phase 13 of doc 20), reusing the current presigned-GET playback component.

---

## 16. Open questions (resolve in the repository audit)

1. Does the current annotation worker keep bboxes per track per frame in a form it can return? (§11.8)
2. Does the current MP4 output contain an audio stream? (§12.2)
3. Is the current output encoded twice (OpenCV `mp4v` → ffmpeg)? (§12.2)
4. What are the real table/column names in doc 16 for §3.2?
5. Are lip/mouth landmarks stored in `feature_extractions`? This does not affect the renderer, but it determines whether the upstream attribution needs an extra pass.
6. What languages will transcripts contain? This determines the fallback fonts to bundle. (§10.4)
