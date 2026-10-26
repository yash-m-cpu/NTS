# 15 — Audio-Visual Fusion Layer

**Project:** NTS (Non-Technical Skills) meeting intelligence
**Status:** Design specification (extends Phases 7–11)
**Companion document:** `16_DATABASE_SPEECH_SCHEMA.md` (DDL, SQLAlchemy models, migrations)

---

## 0. Scope, assumptions, prerequisites

### 0.1 What this layer does

The existing system produces independent streams: CV features (`@vladmandic/human` via `cv_extraction_worker`), STT and speaking turns (`faster-whisper`), and LLM reports built from aggregates. This layer joins them on **one clock** into a **unified, confidence-annotated timeline** of *who said what, how, and how everybody else behaved while they said it*.

Output for a turn looks like this (fully worked in §17):

```
00:10.02–00:17.95   Speaker: P1  (attribution 0.85)
Transcript: "So before we lock the release date, can we check with QA ..."
Pitch 142 Hz · Speech rate 3.3 w/s · Pause ratio 0.11

Listeners:
  P2 → speaker-oriented 82%
  P3 → speaker-oriented 61%
  P4 → possible note-taking 37%

P1 speaking:  mouth activity 0.78 · face confidence 0.93 · attribution confidence 0.85
```

### 0.2 Assumptions about the existing system

I only have the project history summary, not the code. The following are **assumptions to verify** against the actual models before implementation:

| Assumption | Where it matters |
|---|---|
| UUID primary keys on `meetings`, `participant_tracks`, `processing_jobs` | FK types in doc 16 |
| `feature_extractions` holds per-frame or per-window CV rows keyed by `participant_track_id` with a timestamp | §4 source adapters |
| STT turns / speaking ratios are currently stored in `feature_extractions` or `behavioral_metrics` | §12, backfill in doc 16 |
| `processing_jobs` has a string-ish job type and supports cascade triggering via `job_service.py` | §16.3 |
| `human_cv_script.js` runs with face detection + description + emotion + gaze + body + hand | §0.3 |
| MinIO layout already has per-meeting prefixes | §14 |

### 0.3 Prerequisites and known gaps (must be closed first)

1. **Mouth activity is not in the current feature list.** The summary lists head rotation, gaze, body pose, hands, and emotion. Mouth activity (lip aperture over time) needs the face **mesh** landmarks from `human` (`face.mesh.enabled = true`) or a lip-aperture scalar emitted by `human_cv_script.js`. Without it, audio–visual speaker attribution falls back to weaker evidence (§10.4). **Action:** extend the script to emit `mouth_open_ratio` (inner-lip gap ÷ mouth width) plus per-frame `face_conf`.
2. **Per-frame detection confidence and frame timestamps** must be preserved (`pts_ms`, not just a frame index). If the current worker stores only `frame_index`, add `pts_ms` from ffmpeg (`-vf showinfo` or `ffprobe -show_frames`) so variable-frame-rate video is handled correctly (§3).
3. **Dedicated audio extraction.** The fusion layer needs a mono 16 kHz WAV (already implied by `faster-whisper`). Keep it in MinIO as an artifact (`audio/{meeting_id}/mono16k.wav`) so prosody and clock sync do not re-decode video.
4. **Diarization source.** History says `faster-whisper` provides "transcription and diarization". Whisper does not diarize natively, so whichever diarizer is used (pyannote or another), this layer only requires `(speaker_label, start, end)` intervals and treats them as raw evidence.

### 0.4 Ethical and interpretive stance

Listener labels ("speaker-oriented", "possible note-taking") are **observable-behavior proxies**, not mental states. The UI and reports must say "head/gaze oriented toward speaker", never "was paying attention". Every label carries a probability and a coverage figure so unreliable observations are visibly unreliable.

---

## 1. Design principles

| # | Principle | Consequence |
|---|---|---|
| P1 | **Never invent observations** | Interpolation is only for continuous signals and only across short gaps; interpolated samples are flagged and cannot trigger events (§4.3). Missing data is represented explicitly (`DATA_GAP` events, `coverage`, `UNKNOWN` probability mass). |
| P2 | **Raw evidence is immutable** | Fusion reads source rows; it never edits `feature_extractions`, `speech_segments`, or `diarization_segments`. Every derived item carries `evidence_refs` (§14). |
| P3 | **Confidence everywhere** | Every event, attribution, listener label, and turn has a `[0,1]` confidence and the components that produced it. |
| P4 | **Determinism and idempotence** | Same inputs + same config + same version ⇒ same output. Runs are keyed by an input hash so ARQ retries are safe. |
| P5 | **One canonical clock** | All derived times are integer milliseconds on the meeting clock (§3). |
| P6 | **Ambiguity is preserved, not resolved by fiat** | Conflicting attribution keeps ranked candidates; low confidence surfaces as `UNATTRIBUTED`, not as a guess (§8). |
| P7 | **Additive to the existing architecture** | New ARQ jobs, new tables, new endpoints. No change to the upload, CV, or STT pipelines beyond the prerequisites above. |

---

## 2. Architecture and pipeline

### 2.1 Stages (ARQ jobs, cascaded by `job_service.py`)

```
 upload → CV extraction ─┐
                         ├─► [F0] fusion_prepare ─► [F1] speech_prosody ─┐
 STT + diarization ──────┘     (probe, clock sync,  [F2] speech_linguistic├─► [F4] listener_analysis ─► [F5] fusion_assemble
                                normalize inputs)   [F3] speaker_attribution┘        (uses attribution)        (turns, events, rollups)
```

| Stage | Job type (proposed) | Inputs | Outputs |
|---|---|---|---|
| F0 | `FUSION_PREPARE` | media probe, CV rows, diarization, ASR | `fusion_runs` row (clock alignment, coverage), normalized signal artifacts in MinIO |
| F1 | `SPEECH_PROSODY` | mono WAV + `speech_segments` | `speech_prosody_features`, pitch contour artifacts |
| F2 | `SPEECH_LINGUISTIC` | `speech_segments` text | `speech_linguistic_features` |
| F3 | `SPEAKER_ATTRIBUTION` | diarization + mouth activity + face conf | `speaker_attributions` |
| F4 | `LISTENER_ANALYSIS` | CV rows + attribution + turns skeleton | `listener_behavior_segments` |
| F5 | `FUSION_ASSEMBLE` | everything above | `audio_visual_fusion_results`, `speaker_listener_interactions`, `conversation_events`, rollups into `behavioral_metrics` |

F1, F2, F3 are independent and run in parallel after F0. F4 needs F3. F5 needs F1–F4. Each stage is idempotent on `(meeting_id, stage, input_hash)`.

### 2.2 Data flow rule

Stages read **only** from (a) source tables/artifacts and (b) earlier fusion stages of the *same* `fusion_run_id`. This keeps runs self-consistent and lets a whole run be deleted with one cascade.

---

## 3. Time model and clock synchronization

### 3.1 Canonical clock

* `t_ms`: `int64` milliseconds since **meeting clock zero**.
* Meeting clock zero = the presentation timestamp (PTS) of the first decodable **video** frame, after applying `container_start_time` correction. Rationale: the annotated video (Phase 11) and the browser player already use video time, so the frontend seeks without translation.
* Audio times are mapped to the meeting clock by `t_meeting = t_audio + audio_offset_ms + drift_ppm * 1e-6 * t_audio`.
* Floats are used only inside algorithms. **Stored times are integer ms.** Round half-even at the boundary to avoid systematic bias.

### 3.2 Sources of clock error

| Source | Symptom | Handling |
|---|---|---|
| Container `start_time` differs for audio vs video streams | Constant offset (often 0–200 ms) | Read via `ffprobe`, apply as initial offset |
| Variable frame rate video | Frame index ≠ time | Always use per-frame `pts_ms`; never `index / fps` |
| Whisper timestamps | Word times can lag/lead by 100–300 ms; segment boundaries are coarse | Prefer word timestamps; treat ASR boundaries as ±250 ms uncertain |
| Diarization boundaries | ±200–500 ms at turn edges | Widen boundaries when matching to visual events |
| Encoder/recording drift | Linear drift over long meetings | Estimated by lip-sync alignment at multiple anchor windows (§3.3) |
| Trimmed/concatenated media | Step offsets | Detected as discontinuities; segment-wise offsets |

### 3.3 Offset and drift estimation (AV lip-sync alignment)

Goal: estimate `audio_offset_ms` and `drift_ppm` when there is enough face-visible speech. If evidence is weak, **keep the container-derived offset and record low confidence**. Do not force a "better" number.

```python
def estimate_clock_alignment(vad: BinarySignal,          # 100 Hz, from audio energy/VAD
                             mouth: dict[TrackId, Signal],# ~10-30 Hz mouth_open_ratio, valid-mask aware
                             probe: MediaProbe) -> ClockAlignment:
    base = probe.audio_start_ms - probe.video_start_ms      # container offset
    anchors = pick_anchor_windows(vad, mouth,
                                  n=8, win_s=90,
                                  require_single_visible_speaker=True)  # cleanest evidence
    results = []
    for w in anchors:
        # score(lag) = Pearson(vad_shifted, mouth_active) over valid frames only
        lags = range(-600, 601, 20)                       # ms search window
        scores = [masked_corr(shift(w.vad, base + lag), w.mouth) for lag in lags]
        peak = argmax(scores)
        prominence = scores[peak] - median(scores)
        if scores[peak] >= 0.30 and prominence >= 0.15 and w.n_valid >= 200:
            results.append((w.center_s, base + lags[peak], scores[peak]))

    if len(results) < 3:
        return ClockAlignment(offset_ms=base, drift_ppm=0.0, method="CONTAINER_ONLY",
                              confidence=0.5 if probe.has_both_start_times else 0.3,
                              n_anchors=len(results))

    x, y, w = unzip(results)
    offset, drift = robust_linear_fit(x, y, weights=w)   # Huber / RANSAC
    resid = median_abs_residual(x, y, offset, drift)
    conf = clip(1.0 - resid / 150.0, 0.2, 0.95)          # 150 ms resid => 0 credit
    if abs(drift) > 500:                                  # ppm sanity bound
        drift = 0.0; conf *= 0.6
    return ClockAlignment(offset, drift, method="LIPSYNC_FIT", confidence=conf, n_anchors=len(results))
```

The result is stored in `fusion_runs.clock_alignment` (JSONB) and **every derived time inherits a `time_uncertainty_ms`** (default ±120 ms for LIPSYNC_FIT with confidence >0.8; ±250 ms for CONTAINER_ONLY). Event matching windows widen by that uncertainty.

### 3.4 Normalization

All source rows are adapted to a common in-memory shape:

```python
@dataclass(frozen=True)
class Obs:                    # one observation
    t_ms: int                 # meeting clock
    value: float | str | tuple
    conf: float               # source-native confidence, [0,1]; 1.0 only if source is exact
    flags: frozenset[str]     # {"INTERP","LOW_LIGHT","OCCLUDED","EDGE_OF_FRAME",...}
    ref: EvidenceRef          # (table, id) or (artifact_key, offset)

@dataclass
class Signal:
    name: str
    track: TrackId | None
    obs: list[Obs]            # sorted, irregular timestamps allowed
    nominal_hz: float | None
    valid_ranges: list[tuple[int,int]]   # where the *detector was running*
```

`valid_ranges` matters: "no detection in a range where the detector ran" (face not found) is different from "detector did not run" (frames dropped). The first is evidence of absence-of-face; the second is **missing data**.

---

## 4. Signal model, missing data, and interpolation

### 4.1 Missing-data taxonomy

| Case | Definition | Representation |
|---|---|---|
| **Dropped frame** | No CV row for a frame that should exist (given nominal cadence) | Gap in `valid_ranges`; counts against `coverage` |
| **Dropped detection** | Frame processed, subject not detected | Observation with `present=false`, flagged `NO_DETECTION`; not a gap |
| **Low-confidence detection** | Detected, conf below floor | Kept, weighted by conf; excluded from trigger logic if `< floor` |
| **ID switch / track fragmentation** | Track ID changes for the same person | Handled upstream by `participant_tracks`; fusion only *flags* suspicious jumps (bbox jump > threshold within 1 frame) |
| **Missing audio** | No audio stream, or silent/corrupt range | `DATA_GAP{modality:AUDIO}`; no speech events are generated in the range |
| **Missing video** | No video, or range with no frames | `DATA_GAP{modality:VIDEO}`; audio-only turns still emitted, listener sections `null` |
| **Partial modality** | Face visible but body not (etc.) | Per-feature availability recorded in `coverage` |

### 4.2 Coverage

For any window `W` and signal `S`:

```
coverage(S, W) = observed_non_interpolated_duration(S, W) / |W|
```

Only frames where the detector ran **and** produced an observation with `conf ≥ floor` count. Coverage feeds into confidence (§9) and is stored on every listener segment and turn.

### 4.3 Interpolation policy ("interpolate where appropriate, never invent")

| Signal | Interpolate? | Max gap | Method | Conf handling | Can trigger events? |
|---|---|---|---|---|---|
| Head yaw/pitch/roll | Yes | 250 ms | Linear on unwrapped angles | `conf *= exp(-gap/200ms)` | No (only smoothing) |
| Gaze bearing | Yes | 250 ms | Linear on unwrapped angles | same | No |
| Face bbox / centroid | Yes | 300 ms | Linear | same | No |
| Body keypoints | Yes | 200 ms, per keypoint, only if both bracketing samples conf ≥ 0.5 | Linear | same | No |
| Mouth open ratio | Yes | 100 ms | Linear | same | No |
| Emotion probabilities | **No** | — | — | — | — |
| Hand detected / not | **No** | — | — | — | — |
| Face present / absent | **No** | — | — | — | — |
| VAD / diarization intervals | **No** | — | Interval data; tolerance widening only | — | — |
| ASR text / words | **No** | — | — | — | — |
| F0 (pitch) | **No** across unvoiced; ≤ 40 ms octave-error repair only | — | Median filter | conf reduced | — |

Rules:

1. Interpolated observations get `flags ∋ "INTERP"` and are **never counted in coverage**.
2. **Event triggers require ≥ N non-interpolated observations** inside the trigger window (e.g., nod needs ≥ 6 real frames spanning the oscillation).
3. A gap larger than max-gap stays a gap. Smoothing filters (median/Savitzky–Golay) run **per contiguous valid segment**, never across gaps.
4. Nothing is extrapolated beyond the first/last real observation.

---

## 5. Canonical event model

### 5.1 Event schema

```python
class EventClass(str, Enum):
    POINT = "POINT"          # instantaneous (start_ms only)
    INTERVAL = "INTERVAL"    # has end_ms

class ConversationEvent(BaseModel):
    id: UUID
    schema_version: Literal[1] = 1
    event_type: EventType
    event_class: EventClass
    start_ms: int
    end_ms: int | None                  # None for POINT
    time_uncertainty_ms: int            # ± bound propagated from clock alignment + source
    actor: ParticipantRef | None        # who performs it
    target: ParticipantRef | None       # who it is directed at / responds to
    confidence: float                   # [0,1] final
    confidence_components: dict[str, float]
    source_kind: Literal["SPEECH","DIARIZATION","CV","FUSION_RULE","MANUAL"]
    parent_event_id: UUID | None        # RESPONSE→QUESTION, INTERRUPTION→SPEECH_START, etc.
    turn_id: UUID | None                # containing fused turn
    payload: dict                       # type-specific, validated per type
    evidence_refs: list[EvidenceRef]
    quality_flags: list[str]

class ParticipantRef(BaseModel):
    participant_track_id: UUID | None   # None if unattributed speaker
    speaker_label: str | None           # diarization label kept when unattributed
    attribution_confidence: float | None

class EvidenceRef(BaseModel):
    kind: Literal["TABLE","ARTIFACT"]
    table: str | None                   # e.g. "speech_segments"
    id: UUID | None
    artifact_key: str | None            # MinIO key
    range: tuple[int,int] | None        # ms or byte/frame range within artifact
```

### 5.2 Event taxonomy

Requested types plus five additions (marked ★) that the rules below need.

| Type | Class | Actor → Target | Storage (physical) | Trigger summary | Min modalities |
|---|---|---|---|---|---|
| `SPEECH_START` | POINT | speaker | events | Start of a speech segment after ≥ 300 ms of that speaker's silence | audio |
| `SPEECH_END` | POINT | speaker | events | End of speech segment followed by ≥ 300 ms silence for that speaker | audio |
| `SPEAKER_CHANGE` | POINT | from → to | events | Dominant speaker changes between adjacent turns | audio |
| `OVERLAP_START` | POINT | speakers (payload list) | events | ≥ 2 speakers' active intervals intersect for ≥ 200 ms | audio |
| `OVERLAP_END` | POINT | speakers | events | Intersection ends | audio |
| `QUESTION` | INTERVAL | speaker → addressee? | events | Linguistic question classifier ≥ 0.6, optionally boosted by terminal F0 rise | audio+text |
| `INTERRUPTION` | POINT | interrupter → interrupted | events | Speaker B starts inside A's active speech, non-backchannel, A yields or is talked over | audio |
| `RESPONSE` | INTERVAL | responder → asker | events | First substantive turn by addressee/other after a QUESTION within 6 s | audio+text |
| `LISTENER_NOD` | POINT | listener → current speaker | events | Head pitch oscillation criteria (§11.4) | video |
| `LISTENER_GAZE` | INTERVAL | listener → speaker/other | **listener_behavior_segments** | Sustained gaze/head orientation toward a target ≥ 1 s | video |
| `NOTE_TAKING` | INTERVAL | listener | **listener_behavior_segments** | Sustained head-down + hand motion criteria (§11.5) | video |
| `DISTRACTION` | INTERVAL | listener | **listener_behavior_segments** | Sustained off-target orientation with non-task pattern (§11.6) | video |
| `AGREEMENT` | POINT/INTERVAL | speaker → previous speaker | events | Agreement speech-act ≥ 0.6, optionally corroborated by listener nod | text (+video) |
| `DISAGREEMENT` | POINT/INTERVAL | speaker → previous speaker | events | Disagreement speech-act ≥ 0.6 | text |
| `BACKCHANNEL` ★ | POINT | listener speaker | events | Short (≤ 1 s, ≤ 3 words) acknowledgement overlapping/adjacent to another's turn | audio+text |
| `LONG_PAUSE` ★ | INTERVAL | none (meeting-level) | events | Silence ≥ 2.0 s between turns | audio |
| `ADDRESSEE_MENTION` ★ | POINT | speaker → named track | events | Name/role of a participant mentioned; requires a name map | text |
| `DATA_GAP` ★ | INTERVAL | none | events | Modality unavailable (§4.1) | any |

**Logical vs physical storage.** `LISTENER_GAZE`, `NOTE_TAKING`, `DISTRACTION` are *states* with duration, evidence, and coverage, and there can be many per listener. They live in `listener_behavior_segments`. The timeline/API layer **exposes them as events** through the `v_conversation_timeline` view (doc 16 §5), so consumers see one uniform event stream and there is no duplicate storage.

### 5.3 Per-type payload examples

```jsonc
// QUESTION
{"question_type":"YES_NO","terminal_f0_slope_st_per_s":+4.2,"addressee_hint":null,"text_span":[0,26]}

// INTERRUPTION
{"overlap_ms":820,"interrupted_speaker_yielded":true,"yield_latency_ms":640,
 "interrupter_words":["Sorry","but","that's","not"]}

// LISTENER_NOD
{"n_cycles":2,"amplitude_deg":7.8,"freq_hz":1.9,"during_turn_id":"..."}

// DATA_GAP
{"modality":"VIDEO","cause":"NO_FRAMES","affected_tracks":["..."],"coverage_in_range":0.0}
```

---

## 6. Timeline schema

### 6.1 Structure

```
Timeline
 ├─ meta        (meeting_id, fusion_run_id, versions, clock alignment, generated_at)
 ├─ participants[]  (track id, display label P1..Pn, speaker_label map, mapping confidence)
 ├─ coverage    (per modality × per participant, gaps list)
 ├─ turns[]     (FusedTurn, ordered, non-overlapping by primary speaker)
 │    ├─ speech (segments, transcript, prosody summary, linguistics summary)
 │    ├─ speaker_visual (mouth activity, face conf, attribution)
 │    ├─ listeners[] (SpeakerListenerInteraction)
 │    ├─ events[]   (events whose start lies in the turn)
 │    └─ quality    (overall confidence, flags)
 └─ gaps[]      (silence turns and DATA_GAP intervals)
```

Turns are ordered and, by construction, do not overlap **by primary speaker**. Simultaneous speech is represented by `OVERLAP_*` events plus `overlap` info inside the turn that loses the primary role.

### 6.2 FusedTurn

```python
class FusedTurn(BaseModel):
    id: UUID
    seq: int
    kind: Literal["TURN","GAP"]
    start_ms: int
    end_ms: int
    speaker: ParticipantRef | None
    speech: SpeechBlock | None
    speaker_visual: SpeakerVisualBlock | None       # None when no video
    listeners: list[ListenerBlock]                  # [] when no video
    events: list[ConversationEventRef]              # ids + type + start for compactness
    overall_confidence: float
    coverage: CoverageBlock                         # audio, video, per-listener
    quality_flags: list[str]

class SpeechBlock(BaseModel):
    segment_ids: list[UUID]
    transcript: str                                 # joined at read time from speech_segments
    asr_confidence: float | None
    prosody: ProsodySummary | None                  # duration-weighted rollup, cached
    linguistic: LinguisticSummary | None

class ProsodySummary(BaseModel):
    f0_mean_hz: float | None
    f0_range_semitones: float | None
    speech_rate_wps: float | None
    articulation_rate_wps: float | None
    pause_ratio: float | None
    energy_mean_db: float | None
    baseline_z: dict[str, float] | None             # vs. this speaker's own baseline
    reliability: float                              # voiced frames, SNR, overlap

class SpeakerVisualBlock(BaseModel):
    track_id: UUID | None
    mouth_activity: float | None                    # fraction of valid frames with mouth active
    face_confidence: float | None                   # mean detection conf, non-interpolated
    visual_coverage: float                          # observed non-interp / turn duration
    attribution_confidence: float | None

class ListenerBlock(BaseModel):
    track_id: UUID
    top_label: ListenerLabel
    top_probability: float
    label_probs: dict[ListenerLabel, float]         # includes UNKNOWN
    display_text: str                               # server-composed: "possible note-taking 37%"
    coverage: float
    reliability: float
    counts: dict[str,int]                           # nods, gaze_shifts
```

### 6.3 Concrete timeline JSON (abridged)

See §17.4 for the full worked instance.

---

## 7. Fusion algorithm

### 7.1 Top level

```python
async def run_fusion(meeting_id, fusion_run_id, cfg: FusionConfig) -> None:
    src   = await load_sources(meeting_id, cfg)                  # adapters, no mutation
    clock = estimate_clock_alignment(src.vad, src.mouth, src.probe)      # §3.3
    S     = normalize(src, clock)                                 # Signals on meeting clock (§3.4)
    gaps  = detect_gaps(S)                                        # -> DATA_GAP events, valid_ranges

    attr  = attribute_speakers(S, cfg)                            # §10  (F3)
    turns = assemble_turns(S.diarization, S.speech, attr, cfg)    # §7.2
    L     = analyze_listeners(S, turns, attr, cfg)                # §11  (F4)
    pros  = load_prosody(fusion_run_id)                           # §12  (F1)
    ling  = load_linguistic(fusion_run_id)                        # §12  (F2)

    events = []
    events += speech_events(turns, S)                             # start/end/change/overlap/pause
    events += linguistic_events(turns, ling, pros, cfg)           # question/agree/disagree/backchannel
    events += interaction_events(turns, events, cfg)              # response/interruption
    events += listener_point_events(L)                            # nods
    events += gaps

    events = resolve_conflicts(events, S, attr)                   # §8
    for ev in events: ev.confidence, ev.confidence_components = propagate(ev, S, attr)   # §9

    interactions = build_interactions(turns, L, events)           # per turn × listener
    rollups      = compute_rollups(turns, interactions, events, pros)   # -> behavioral_metrics

    await persist(fusion_run_id, turns, events, L, interactions, rollups)   # single transaction
```

### 7.2 Turn assembly

Input: diarization intervals (raw), ASR segments (with word times), attribution.

```python
def assemble_turns(dia, speech, attr, cfg):
    # 1. Split ASR segments at diarization boundaries using word timestamps.
    #    Whisper segments can span two speakers; words cannot.
    words = explode_words(speech)                          # (t_start, t_end, text, prob, seg_id)
    for w in words:
        w.speaker_label = label_with_max_overlap(w, dia, tol_ms=cfg.boundary_tol_ms)   # may be None

    # 2. Merge consecutive words with same speaker_label into utterances.
    utts = group_runs(words, key=lambda w: w.speaker_label,
                      max_internal_silence_ms=cfg.same_turn_gap_ms)   # default 800

    # 3. Merge utterances of the same speaker into turns when the gap is < cfg.same_turn_gap_ms
    #    and no other speaker's *substantive* utterance intervenes.
    #    Backchannels do NOT break a turn.
    turns = []
    for u in utts:
        if turns and turns[-1].speaker_label == u.speaker_label \
           and u.start - turns[-1].end < cfg.same_turn_gap_ms:
            turns[-1].extend(u)
        elif is_backchannel(u) and turns and overlaps_or_adjacent(u, turns[-1]):
            turns[-1].backchannels.append(u)               # attaches, emits BACKCHANNEL later
        else:
            turns.append(Turn.from_utt(u))

    # 4. Resolve speaker identity via attribution (§10). Unattributed stays unattributed.
    for t in turns:
        t.speaker = attr.resolve(t.speaker_label, t.span)  # ParticipantRef (possibly track=None)

    # 5. Insert GAP items for silences >= cfg.min_gap_ms (default 500). Silence is an observation
    #    only if audio is valid there; else it's a DATA_GAP, not a GAP.
    return with_gaps(turns, valid_audio_ranges)
```

Words with no diarization label (`speaker_label=None`, diarizer missed speech) form `UNATTRIBUTED_SPEECH` turns: text kept, speaker `None`, confidence capped at 0.5.

### 7.3 Speech event derivation (examples)

```python
def speech_events(turns, S):
    ev = []
    for t in turns.of_kind("TURN"):
        ev.append(point("SPEECH_START", t.start, t.speaker, refs=t.segment_refs))
        ev.append(point("SPEECH_END",   t.end,   t.speaker, refs=t.segment_refs))
    for a, b in pairwise(turns.of_kind("TURN")):
        if a.speaker.key != b.speaker.key:
            ev.append(point("SPEAKER_CHANGE", b.start, actor=b.speaker, target=a.speaker,
                            payload={"gap_ms": b.start - a.end}))
    for iv in intersections_of_active_speech(S.diarization, min_ms=200):
        ev.append(point("OVERLAP_START", iv.start, payload={"speakers": iv.speakers}))
        ev.append(point("OVERLAP_END",   iv.end,   payload={"speakers": iv.speakers}))
    for g in silences(turns, min_ms=2000):
        ev.append(interval("LONG_PAUSE", g.start, g.end))
    return ev
```

### 7.4 Interaction events

```python
def interaction_events(turns, events, cfg):
    out = []
    # RESPONSE: first substantive turn by someone else within cfg.response_window_ms of a QUESTION end
    for q in events.of_type("QUESTION"):
        nxt = first(t for t in turns if t.start >= q.end_ms - cfg.overlap_tol_ms
                    and t.speaker.key != q.actor.key and not t.is_backchannel_only)
        if nxt and nxt.start - q.end_ms <= cfg.response_window_ms:            # 6000
            addressed = (q.target is None) or (nxt.speaker.key == q.target.key)
            out.append(interval("RESPONSE", nxt.start, nxt.end,
                                actor=nxt.speaker, target=q.actor, parent=q.id,
                                payload={"latency_ms": nxt.start - q.end_ms,
                                         "addressed_as_expected": addressed}))
    # INTERRUPTION: B starts within A's active speech
    for ov in events.of_type("OVERLAP_START"):
        a, b = who_was_first(ov), who_started_later(ov)
        if not is_backchannel(b.utterance_at(ov.start)) and ov.duration >= 300 \
           and a.remaining_speech_after(ov.start) >= 500:        # A had more to say
            yielded = a.stops_within(ov.start, 1500)
            out.append(point("INTERRUPTION", ov.start, actor=b.ref, target=a.ref,
                             payload={"overlap_ms": ov.duration,
                                      "interrupted_speaker_yielded": yielded}))
    return out
```

INTERRUPTION and BACKCHANNEL intentionally share the overlap trigger; the classifier `is_backchannel` (short, ≤ 3 words, low-content lexicon, low energy, listener not taking the floor) separates them. Ambiguous cases yield **both** candidates only if each ≥ 0.35; otherwise the higher wins (§8).

---

## 8. Conflict resolution

### 8.1 Precedence by question

Different modalities are authoritative for different questions. Conflicts are resolved **per question**, not by a global modality ranking.

| Question | Authoritative | Supporting | Never authoritative |
|---|---|---|---|
| Was there speech at time t? | Audio (VAD / ASR / diarization) | — | Video mouth movement |
| What was said? | ASR | — | Everything else |
| When did it start/end? | ASR word times ∩ diarization, corrected by clock alignment | VAD | Video |
| Who (diarization label) spoke? | Diarization | ASR turn structure | — |
| Which **person on camera** is that speaker? | AV attribution (lip-sync correlation) + manual override | Face-ROI, room geometry, priors | Diarization alone (has no visual identity) |
| Was a listener nodding / looking / writing? | CV features | Speech context (only to *interpret*, not to detect) | Audio |
| Is it a question / agreement? | Linguistic features | Prosody (boost), listener nod (corroboration) | Video alone |

### 8.2 Conflict cases and rules

| # | Conflict | Rule |
|---|---|---|
| C1 | Diarization says label X spoke; the attributed person's mouth is closed for the whole turn | Keep the turn and label. Lower attribution confidence via the `mouth_activity` term. If the confidence falls below `attr_floor` (0.4), set `speaker.track = None` (`UNATTRIBUTED`) and keep candidates. Emit quality flag `ATTRIBUTION_VISUAL_MISMATCH`. |
| C2 | Two candidate tracks with similar sync scores | Keep ranked candidates in `speaker_attributions`. Selected = best only if margin ≥ 0.15; else `UNATTRIBUTED`, flag `AMBIGUOUS_ATTRIBUTION`. |
| C3 | Mouth moves, no audio speech at that time | **No speech event.** Record `MOUTH_ACTIVITY_WITHOUT_AUDIO` as an evidence flag on the person's visual coverage (possible muted mic, singing/mouthing, off-mic). Never create a turn. |
| C4 | ASR text exists, VAD says silence | Keep text with `ASR_NO_VAD` flag and `asr_confidence *= 0.5` (likely hallucination on noise; Whisper does this). |
| C5 | Speech (VAD/energy) present, diarizer has no label | `UNATTRIBUTED_SPEECH` turn (§7.2). |
| C6 | Diarization label maps to two different tracks across the meeting | Cluster-level attribution keeps the best global assignment. Segment-level overrides are allowed only with `local_score − cluster_score ≥ 0.25` and are flagged `SEGMENT_OVERRIDE`. |
| C7 | Overlapping speech, one speaker's words unrecoverable | Primary = louder/longer speaker. The quieter speaker gets `OVERLAP` event with `transcript_available:false`. No fabricated text. |
| C8 | Listener label contradiction (nod during gaze-away segment) | Both are recorded. They are different features, and label probabilities derive from the same evidence so they cannot contradict inside one window. Across adjacent windows, apply the hysteresis of §11.7. |
| C9 | Question classifier disagrees with prosody (falling intonation) | Linguistic decides the type. Prosody may only adjust confidence (±0.1). |
| C10 | Human correction (manual speaker map) | Wins over everything. Stored as attribution with `method=MANUAL`, `confidence=1.0`, and dependent outputs recomputed. |
| C11 | Two events of incompatible types on the same actor/time (e.g., INTERRUPTION vs BACKCHANNEL) | Keep the higher-confidence if the gap ≥ 0.2, else keep both flagged `AMBIGUOUS_TYPE`. |

### 8.3 Resolution procedure

```python
def resolve_conflicts(events, S, attr):
    events = dedupe(events, key=lambda e: (e.event_type, e.actor.key, round(e.start_ms, -2)))
    for group in incompatible_groups(events, INCOMPATIBLE_PAIRS):
        ranked = sorted(group, key=lambda e: e.confidence, reverse=True)
        if ranked[0].confidence - ranked[1].confidence >= 0.2:
            for loser in ranked[1:]: loser.suppressed_by = ranked[0].id      # kept in DB, hidden by default
        else:
            for e in group: e.quality_flags.append("AMBIGUOUS_TYPE")
    return events
```

Suppressed events are **not deleted**. They remain queryable (`include_suppressed=true`), which preserves audit and lets thresholds be tuned later.

---

## 9. Confidence propagation

### 9.1 Definitions

* Confidence is a **calibrated-intent** score in [0,1]: "probability the stated observation is correct". It starts as heuristic scores and should be recalibrated on labeled meetings (§18.4). Until then, the UI labels it "confidence" not "probability".
* **Reliability** (of a measurement window): how trustworthy the *inputs* were (coverage, detector confidence, SNR). Separate from **evidence strength** (how strongly the inputs indicate a label).

### 9.2 Rules

| Situation | Rule | Formula |
|---|---|---|
| Dependency chain (A needs B needs C) | Product | `c = c_A · c_B · c_C` |
| Independent corroboration (two modalities agree) | Log-odds sum with correlation discount ρ | `logit(c) = logit(c₁) + (1−ρ)·logit(c₂)` (ρ default 0.3; cap at 0.99) |
| Contradiction | Subtract in log-odds | `logit(c) = logit(c₁) − (1−ρ)·logit(c₂)` |
| Interpolated sample | Decay by gap | `c' = c · exp(−gap_ms / τ)`, τ = 200 ms |
| Coverage | Multiplicative reliability | `r = coverage · mean(frame_conf)` |
| Clock uncertainty | Widens windows and multiplies | `c' = c · (1 − min(0.3, u_ms/1000))` where `u_ms` is the time uncertainty |
| Never certain | Clip | `c ∈ [0.01, 0.99]` (manual = 1.0 exempt) |

### 9.3 Component structure

Each event stores `confidence_components` for explainability:

```json
{"asr": 0.91, "attribution": 0.85, "classifier": 0.88, "prosody_boost": 0.04,
 "clock": 0.96, "coverage": 0.94}
```

### 9.4 Worked example (QUESTION at 10.02 s, P1)

```
classifier (text)         = 0.88
prosody terminal rise     → corroboration c₂ = 0.70, ρ = 0.3
  logit(0.88) = 1.99 ; logit(0.70) = 0.85
  combined logit = 1.99 + (1 − 0.3)·0.85 = 2.585  →  c = 0.930
ASR confidence            = 0.91
clock factor              = 1 − min(0.3, 0.120) = 0.88     (time uncertainty ±120 ms)

event_confidence  = 0.930 · 0.91 · 0.88 = 0.745  → 0.75
actor_confidence  = attribution confidence      = 0.85
```

Design note: multiplying attribution into a *speech-content* property (that a question was asked at that time) would be too harsh, because the question happened regardless of whom we attribute it to. Confidence is therefore split in two. `confidence` is the **event** confidence (that a QUESTION occurred), and `actor.attribution_confidence` is the confidence that the actor is P1. Both are exposed by the API. The full product (`0.75 · 0.85 ≈ 0.64`) is used only for aggregate NTS features where identity matters, such as "P1 asked N questions".

### 9.5 Display buckets

| Probability / confidence | Label wording |
|---|---|
| ≥ 0.60 | stated plainly ("speaker-oriented 82%") |
| 0.35 – 0.60 | prefixed "possible" ("possible note-taking 37%") |
| < 0.35 | "uncertain" or not shown |
| `UNKNOWN` mass > 0.5 | "insufficient visual evidence" |

---

## 10. Speaker attribution integration

### 10.1 Two levels

1. **Cluster-level**: map each diarization `speaker_label` (e.g., `SPEAKER_01`) to a `participant_track`, the stable global assignment.
2. **Segment-level**: exceptions where a specific diarization segment is better explained by a different track (diarizer confusion) or by no visible track.

Stored in one table (`speaker_attributions`, scope `CLUSTER|SEGMENT`); segment scope overrides cluster scope when selected.

### 10.2 Evidence sources

| Method | Signal | Strength | Requires |
|---|---|---|---|
| `AV_SYNC` | Correlation between speaker's VAD indicator and each track's mouth activity | Strong | mouth aperture, valid face frames |
| `FACE_ROI` | Speaker-ID embeddings vs face embeddings (optional future) | Medium | model outside current stack |
| `ROOM_GEOMETRY` | Direction-of-arrival from multichannel audio | Medium | multichannel audio (rare) |
| `PRIOR` | Fewer tracks than clusters, sole visible person, enrolment | Weak | — |
| `MANUAL` | UI correction | Absolute | user |

### 10.3 Algorithm

```python
def attribute_speakers(S, cfg):
    clusters = S.diarization.labels()                       # SPEAKER_00..K
    tracks   = S.participant_tracks                         # persons on camera
    # --- Score matrix: sync score per (cluster, track)
    M = np.zeros((len(clusters), len(tracks)))
    N = np.zeros_like(M)                                    # n valid frames supporting each score
    for i, c in enumerate(clusters):
        vad_c = indicator(S.diarization.intervals(c), hz=10)   # exclusive-speech frames only
        for j, t in enumerate(tracks):
            a_t = S.mouth[t].resample_valid(hz=10)             # non-interpolated frames only
            m = valid_mask(vad_c, a_t) & ~overlap_mask         # ignore overlap frames
            if m.sum() < cfg.min_frames:      continue         # leave score 0, N small
            r = pearson(vad_c[m], a_t.value[m])
            M[i, j] = r * min(1.0, m.sum() / cfg.n_full)       # shrink by support
            N[i, j] = m.sum()
    # --- Global 1:1 assignment (a person is one voice); allow "no visible person" per cluster
    cost = -np.pad(M, ((0,0),(0,len(clusters))), constant_values=cfg.null_score)  # null_score≈0.15
    rows, cols = linear_sum_assignment(cost)
    result = []
    for i, j in zip(rows, cols):
        best   = M[i, j] if j < len(tracks) else None
        second = second_best_excluding(M[i], j)
        if best is None:
            result.append(Attribution(cluster=clusters[i], track=None, method="AV_SYNC",
                                      confidence=0.0, candidates=rank(M[i])))
            continue
        margin = best - second
        face_q = mean_conf(S.face_conf[tracks[j]], where=cluster_active(i))
        cov    = N[i, j] / total_active_frames(i)
        conf   = sigmoid(cfg.k * margin) * face_q * min(1, cov)          # k≈6
        selected = conf >= cfg.attr_floor
        result.append(Attribution(cluster=clusters[i],
                                  track=tracks[j] if selected else None,
                                  confidence=conf, candidates=rank(M[i]), components={
                                      "sync_score": best, "margin": margin,
                                      "face_conf": face_q, "coverage": cov}))
    result += segment_level_overrides(S, result, cfg)                    # C6
    result = apply_manual_overrides(result, S.manual_map)                # C10
    return result
```

### 10.4 Degraded modes

| Situation | Behavior |
|---|---|
| No mouth signal (prereq §0.3 unmet) | Use `PRIOR` (only if #visible tracks == #clusters and geometry unambiguous) with confidence ≤ 0.4; otherwise everything is `UNATTRIBUTED`. Speech analytics still work per `speaker_label`. |
| Single speaker + single track | `PRIOR` 0.7, raised to 0.85 by any sync corroboration |
| Speaker off-camera | Cluster gets `track=None`, still a first-class participant (`speaker_label`) in the timeline |
| Speaker changes seat / re-entered frame | Handled by track ID change → segment-scope attribution |

### 10.5 Worked scores (the 10–18 s window)

```
cluster SPEAKER_01 vs   P1: r=0.78 · shrink(0.91) = 0.71    P2: 0.09   P3: 0.05   P4: −0.02
margin = 0.62 ; sigmoid(6·0.62)=0.976 ; face_q = 0.93 ; cov = 0.94
attribution_confidence = 0.976 · 0.93 · 0.94 = 0.853 → 0.85
```

---

## 11. Listener integration

### 11.1 Spatial modes

Listener orientation needs a definition of "toward the speaker", which depends on capture geometry. The mode is inferred once per meeting (stored in `fusion_runs.config.spatial_mode`; overridable by users):

| Mode | Setting | "On speaker" definition |
|---|---|---|
| `ROOM_CAMERA` | One camera, several people in one room | Angle between listener's head/gaze yaw and the bearing to the speaker's face centroid, within tolerance `θ` (default 25°, widened by yaw noise) |
| `GALLERY` | Video conference, one tile per person | "On speaker" = looking toward the screen region; per-tile `looking_at_screen` is a weaker proxy. Attributed to the speaker tile only if the tile layout is known (never assume). |
| `UNKNOWN` | Ambiguous | Only generic states: `LOOKING_FORWARD`, `HEAD_DOWN`, `AWAY`. No "speaker-oriented" label is produced. |

### 11.2 Per-window features (per listener × turn window)

Computed on **non-interpolated, `conf ≥ floor`** frames only:

| Feature | Definition |
|---|---|
| `on_target_ratio` | fraction of observed frames where orientation is on the speaker |
| `head_pitch_mean`, `head_pitch_std` | degrees; positive = down (convention fixed in the adapter) |
| `gaze_down_ratio` | fraction with gaze/head pitch below `−20°` |
| `hand_motion_low` | lower-frame hand keypoint speed above threshold, normalized by body size |
| `hand_near_desk_ratio` | wrist keypoints in bottom third of the person's box |
| `nod_count` | oscillation detections (§11.4) |
| `off_target_ratio` | fraction of frames oriented outside the tolerance and not head-down |
| `coverage`, `mean_frame_conf` | reliability inputs |

### 11.3 Label probabilities

Transparent rule scores in [0,1], normalized, with explicit `UNKNOWN` mass from reliability:

```python
LABELS = ["SPEAKER_ORIENTED","NOTE_TAKING","DISTRACTED","NEUTRAL"]   # + UNKNOWN

def listener_probs(f: WindowFeatures) -> dict[str,float]:
    r = {
      "SPEAKER_ORIENTED": f.on_target_ratio,
      "NOTE_TAKING":      note_taking_score(f),          # §11.5
      "DISTRACTED":       distraction_score(f),          # §11.6
      "NEUTRAL":          neutral_score(f),              # forward, off speaker, no other pattern
    }
    reliability = f.coverage * f.mean_frame_conf
    s = sum(r.values()) or 1.0
    p = {k: reliability * v / s for k, v in r.items()}
    p["UNKNOWN"] = 1.0 - reliability
    return p
```

Worked values for the example turn:

| Listener | r_oriented | r_note | r_other | reliability | Result |
|---|---|---|---|---|---|
| P2 | 0.88 | 0.02 | 0.10 | 0.93 (cov 0.96 × conf 0.97) | oriented = 0.93·0.88 = **0.82** |
| P3 | 0.70 | 0.10 | 0.20 | 0.87 | oriented = 0.87·0.70 = **0.61** |
| P4 | 0.30 | 0.475 | 0.225 | 0.78 (partial occlusion) | note-taking = 0.78·0.475 = **0.37** → shown as "possible note-taking 37%" (UNKNOWN = 0.22) |

### 11.4 Nod detection

Applied to head pitch (after per-segment smoothing, never across gaps):

```python
def detect_nods(pitch: Signal, min_real_frames=6):
    for seg in contiguous_valid_segments(pitch, max_gap_ms=250):
        x = detrend(seg.non_interp_values(), window_s=1.0)
        for w in sliding_windows(x, dur_s=1.2, step_s=0.2):
            if w.n_real < min_real_frames: continue
            peaks = zero_cross_peaks(w, min_amp_deg=4.0)
            f = dominant_freq(w)
            if len(peaks) >= 2 and 0.8 <= f <= 3.5 and yaw_std(w) < 8.0:  # not a head turn
                yield Nod(t=w.center, amp=mean(abs(peaks)), freq=f,
                          conf=nod_conf(len(peaks), w.mean_conf, w.n_real/w.n_expected))
```

### 11.5 Note-taking

Requires **sustained** (≥ 2.0 s) head-down (pitch ≥ +15° or gaze-down) **and** either lower-frame hand motion or wrist-near-desk. Head-down without hand evidence yields at most a `NOTE_TAKING` probability of 0.4 (phone/laptop/reading confusion), so it is displayed as "possible". Hand keypoints must be real, non-interpolated.

### 11.6 Distraction

`DISTRACTED` is deliberately conservative: sustained (≥ 3 s) off-target orientation with either repeated large yaw changes or a face-turned-away pose, and **not** head-down with hand activity. Wording in UI: "oriented away". Not "distracted", unless the user opts into interpretive wording.

### 11.7 Segmenting and hysteresis

Per-listener probabilities are computed on sliding windows (2 s, step 0.5 s) and turned into segments by a small state machine with hysteresis (enter ≥ 0.55, exit < 0.40, min duration 1.0 s, merge gaps < 0.7 s). Segments store the mean probability, coverage, interpolated ratio, and evidence pointers.

### 11.8 Turn-level interaction rows

For each turn × listener: window features over the turn span → `label_probs` → one `speaker_listener_interactions` row. Counts (nods, gaze shifts), mutual-gaze ratio (if the speaker looks at the listener), and `response_latency_ms` (if the listener speaks next) are attached.

---

## 12. Speech analytics integration

### 12.1 Sources and granularity

| Feature group | Producer | Grain | Notes |
|---|---|---|---|
| ASR text, words | `faster-whisper` | segment (+ words in JSONB) | word probs feed ASR confidence |
| Diarization | diarizer | segment | boundary tolerance applies |
| Prosody | new F1 worker (Praat via `parselmouth`, or `librosa.pyin`) | per speech segment | contours to MinIO; aggregates to DB |
| Linguistic | new F2 worker (rules + small classifier) | per speech segment | question, speech-act, sentiment, backchannel, hedge/filler counts |

### 12.2 Prosody definitions (fixed for reproducibility)

| Metric | Definition |
|---|---|
| `f0_mean_hz`, `f0_median_hz` | over voiced frames, octave-error filtered |
| `f0_range_semitones` | 5th–95th percentile in semitones re: 100 Hz |
| `speech_rate_wps` | `word_count / segment_duration` (includes pauses) |
| `articulation_rate_wps` | `word_count / (duration − pause_time)` |
| `pause` | silence ≥ 200 ms **within** the segment between words |
| `pause_ratio` | `pause_time / segment_duration` |
| `energy_mean_db` | RMS dBFS over voiced frames (relative, not calibrated SPL) |

### 12.3 Per-turn rollup

Duration-weighted aggregation of segment rows (weights = voiced duration; pause_ratio and rate weighted by segment duration). The rollup is cached in `audio_visual_fusion_results.prosody_summary` and marked derived; segment-level rows remain the source of truth.

### 12.4 Speaker baselines

Absolute pitch and rate are meaningless across people. Per-speaker baselines (median and MAD of f0, rate, pause ratio over that speaker's **reliable** segments in the meeting) are stored in `behavioral_metrics` (existing table, new metric names, no new table). `baseline_z` in turn summaries is computed against them:

```python
z = (turn_value − baseline.median) / max(baseline.mad·1.4826, eps)
```

Only speakers with ≥ 60 s of reliable voiced speech get baselines. Others get `baseline_z = null`.

### 12.5 Prosody reliability

`reliability = min(1, voiced_frames / 80) · snr_factor · (1 − overlap_fraction)`. A window with heavy overlap or very low SNR carries prosody values but a low `reliability`, and the UI mutes them.

---

## 13. Missing-data handling matrix (end-to-end)

| Scenario | Audio events | Speaker attribution | Listener block | Turn confidence | Flags |
|---|---|---|---|---|---|
| Everything present | full | AV_SYNC | full | full | — |
| Video missing entire meeting | full | `UNATTRIBUTED` (labels kept) | `[]` | audio-only, no visual terms | `NO_VIDEO` |
| Video gap 20–35 s | full | inherits cluster mapping (`cluster` scope only, no local evidence) | `null` in gap turns; partial coverage if straddling | reduced by coverage | `VIDEO_GAP` |
| Audio missing entire meeting | none | n/a | **only generic** (no "speaker-oriented" since no speaker) | n/a | `NO_AUDIO`, listener states limited to non-speaker-relative |
| Audio gap 60–75 s | none in gap; `DATA_GAP` event | unchanged | states continue (visual-only) | n/a | `AUDIO_GAP` |
| Dropped frames (10% random) | full | uses valid frames | coverage 0.9 → reliability drops | reduced | `LOW_VIDEO_COVERAGE` if < 0.6 |
| Track lost 3 s then reacquired | full | unchanged | `UNKNOWN` mass in the 3 s | reduced | `TRACK_GAP` |
| Diarizer failure | ASR-only turns (`UNATTRIBUTED_SPEECH`) | none | needs speaker → generic only | ≤ 0.5 | `NO_DIARIZATION` |
| ASR failure | diarization-only turns without text | AV_SYNC still works | works | no linguistic events | `NO_ASR` |

---

## 14. Raw evidence preservation

1. **Source rows are never rewritten.** Fusion reads `feature_extractions`, `speech_segments`, `diarization_segments`.
2. Derived rows carry `evidence_refs` (JSONB array of `EvidenceRef`), for example:
   ```json
   [{"kind":"TABLE","table":"speech_segments","id":"…"},
    {"kind":"TABLE","table":"diarization_segments","id":"…"},
    {"kind":"ARTIFACT","artifact_key":"fusion/{run}/mouth_P1.parquet","range":[10020,17950]}]
   ```
3. **Normalized signals** (after clock alignment and gap flags) are written once per run as Parquet in MinIO: `fusion/{meeting_id}/{run_id}/signals/{signal}_{track}.parquet`, with columns `t_ms, value, conf, flags, src_row_id`. This is the replayable input to F3/F4/F5.
4. **Prosody contours** (100 Hz F0/energy) live in MinIO: `fusion/{meeting_id}/{run_id}/prosody/{segment_id}.npz`. Only aggregates go to PostgreSQL, so the DB doesn't take millions of frame rows.
5. **Frontend "Why?" popover** fetches `/fusion/turns/{id}/evidence`, which resolves refs and returns presigned GET URLs for artifacts.
6. Every run stores `config`, `code_version`, `model_versions`, and `input_hash` in `fusion_runs`, so any output can be reproduced.

---

## 15. Database representation (summary)

Full DDL and SQLAlchemy models are in `16_DATABASE_SPEECH_SCHEMA.md`.

| Fusion concept | Table |
|---|---|
| Run header, clock alignment, coverage, config | `fusion_runs` |
| ASR segments | `speech_segments` |
| Diarizer output | `diarization_segments` |
| Speaker identity mapping | `speaker_attributions` |
| Prosody aggregates | `speech_prosody_features` |
| Text features | `speech_linguistic_features` |
| Listener states (gaze / note-taking / distraction) | `listener_behavior_segments` |
| Point events, interaction events, gaps | `conversation_events` |
| Fused turns / gaps | `audio_visual_fusion_results` |
| Turn × listener rows | `speaker_listener_interactions` |
| Aggregates for NTS scoring | existing `behavioral_metrics` (+ nullable `fusion_run_id`) |

Time is `BIGINT` milliseconds everywhere. Confidence is `REAL` in [0,1].

---

## 16. API representation

### 16.1 Endpoints (FastAPI, `/api/v1`, org-scoped through the existing `get_current_org` dependency)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/meetings/{id}/fusion/runs` | Enqueue a fusion run (idempotent; returns 202 + job). Body: `{force?: bool, config_overrides?: {}}` |
| `GET` | `/meetings/{id}/fusion/runs` | List runs (status, versions, coverage) |
| `GET` | `/meetings/{id}/fusion/runs/current` | Current run header |
| `GET` | `/meetings/{id}/fusion/timeline` | Paged, filtered timeline (turns + embedded events/listeners) |
| `GET` | `/meetings/{id}/fusion/events` | Flat event stream, filterable (`type`, `actor`, time range, `min_confidence`) |
| `GET` | `/meetings/{id}/fusion/turns/{turn_id}` | One turn with full detail |
| `GET` | `/meetings/{id}/fusion/turns/{turn_id}/evidence` | Resolved evidence with presigned URLs |
| `GET` | `/meetings/{id}/fusion/listeners/{track_id}/segments` | Listener state segments for a participant |
| `GET` | `/meetings/{id}/fusion/quality` | Coverage/gap report |
| `PUT` | `/meetings/{id}/fusion/speaker-map` | Manual attribution override; triggers partial re-run (F4→F5) |

Progress reuses the existing job polling (`useJobPolling`, `processing_jobs`). No new real-time transport.

### 16.2 Timeline query parameters

```
GET /meetings/{id}/fusion/timeline
    ?run_id=<uuid|current>
    &from_ms=0&to_ms=120000
    &speakers=<track_id,...>            # by track; use speaker_label:SPEAKER_02 for unattributed
    &include=prosody,listeners,events,evidence_refs    # default: prosody,listeners
    &min_confidence=0.0
    &include_suppressed=false
    &cursor=<opaque>&limit=100           # keyset on (start_ms, seq)
```

Keyset pagination on `(start_ms, seq)` is index-backed and stable for large meetings. `ETag` is the run's `input_hash` plus the last-modified timestamp, so unchanged timelines are 304s.

### 16.3 Response (turn-level, abridged)

```json
{
  "meta": {
    "meeting_id": "8b1f…", "fusion_run_id": "c07e…", "schema_version": 1,
    "clock": {"method": "LIPSYNC_FIT", "offset_ms": 40, "drift_ppm": 12, "confidence": 0.86},
    "spatial_mode": "ROOM_CAMERA",
    "coverage": {"audio": 0.99, "video": {"P1": 0.94, "P2": 0.96, "P3": 0.90, "P4": 0.81}}
  },
  "participants": [
    {"track_id": "p1…", "label": "P1", "speaker_labels": ["SPEAKER_01"], "mapping_confidence": 0.85},
    {"track_id": "p2…", "label": "P2", "speaker_labels": ["SPEAKER_00"], "mapping_confidence": 0.91}
  ],
  "turns": [ { "...": "see §17.4" } ],
  "next_cursor": "eyJzdGFydF9tcyI6MTgzNTB9"
}
```

### 16.4 Pydantic response models

The `FusedTurn`, `ListenerBlock`, `ConversationEvent` models above are used verbatim as `response_model`. Use `response_model_exclude_none=True` and `by_alias` off. Timestamps are ms integers, and **formatting to `mm:ss.mmm` is client-side only**.

### 16.5 ARQ worker registration (sketch)

```python
class WorkerSettings:
    functions = [fusion_prepare, speech_prosody_worker, speech_linguistic_worker,
                 speaker_attribution_worker, listener_analysis_worker, fusion_assemble_worker]
    max_jobs = 2                     # CPU-bound stages; keep separate from CV/annotation queues
    job_timeout = 3600
    queue_name = "arq:fusion"        # isolate so long CV/annotation jobs don't starve fusion

async def fusion_assemble_worker(ctx, meeting_id: str, fusion_run_id: str, input_hash: str):
    async with ctx["session_factory"]() as db:
        run = await db.get(FusionRun, fusion_run_id)
        if run.stage_done.get("assemble") == input_hash:
            return                                            # idempotent no-op on retry
        await run_fusion_assemble(db, run)                     # single transaction inside
        run.stage_done = {**run.stage_done, "assemble": input_hash}
        await db.commit()
```

Cascade uses the existing `job_service.py` pattern: F0 success enqueues F1–F3, the last of F1–F3 enqueues F4, F4 enqueues F5, and F5 flips `fusion_runs.is_current`.

---

## 17. Concrete end-to-end example

### 17.1 Raw inputs (all times on meeting clock after alignment)

```
diarization_segments
  SPEAKER_01  10020–17950   (no per-segment conf)
  SPEAKER_00  18350–21100
speech_segments
  s1  10040–17930  "So before we lock the release date, can we check with QA about that
                    regression from Tuesday and see if the two blockers are actually closed?"
      asr_conf 0.91, 26 words
  s2  18370–21080  "Yes, QA flagged two blockers yesterday."
mouth_open_ratio (10 Hz, non-interp frames in turn 10–18 s)
  P1: 74/79 frames valid, active in 58 → mouth_activity = 58/74 = 0.78
  P2, P3, P4: low activity (0.06 / 0.04 / 0.03)
face_conf  P1 mean 0.93
head pose / hands
  P2: yaw within 25° of P1 bearing in 82/93 valid frames (coverage 0.96) → 0.88
  P4: head pitch +22° from 11.0–17.0 s, wrist motion in lower frame; 8% frames occluded by laptop
  nods: P2 at 12.40 s (2 cycles, 7.8°, 1.9 Hz)
prosody(s1)
  f0_mean 142 Hz, range 6.1 st, speech_rate 3.3 w/s (26 / 7.89 s),
  articulation 3.7 w/s, pause_ratio 0.11, terminal F0 slope +4.2 st/s, reliability 0.90
linguistic(s1)
  is_question = true (YES_NO, 0.88); s2: speech_act = ANSWER
```

### 17.2 Intermediate results

```
Clock: LIPSYNC_FIT, offset +40 ms, drift 12 ppm, confidence 0.86 → u = ±120 ms
Turn 1: span 10020–17950 (ASR words ∩ diarization), speaker_label SPEAKER_01
Attribution: SPEAKER_01 → P1 (sync 0.71, margin 0.62, face 0.93, cov 0.94) = 0.85
Listeners: P2 0.82 oriented · P3 0.61 oriented · P4 0.37 note-taking (UNKNOWN 0.22)
Events:
  SPEECH_START   10020  P1  conf 0.94
  QUESTION       10040–17930  P1  event_conf 0.75 (§9.4), actor_conf 0.85
  LISTENER_NOD   12400  P2→P1 conf 0.71
  NOTE_TAKING    11000–17000  P4  (segment; prob 0.37 → "possible")
  SPEECH_END     17950  P1
  SPEAKER_CHANGE 18350  P1→P2  gap 400 ms
  RESPONSE       18350–21100  P2→P1  parent=QUESTION, latency 420 ms
```

### 17.3 Rendered text form (what the UI/report shows)

```
00:10.02–00:17.95
Speaker: P1 (attribution 85%)
Transcript: "So before we lock the release date, can we check with QA about that
             regression from Tuesday and see if the two blockers are actually closed?"
Pitch: 142 Hz (range 6.1 st) · Speech rate: 3.3 w/s · Pause ratio: 0.11
Events: QUESTION (75%) · LISTENER_NOD P2 @ 00:12.40

Listeners:
  P2 → speaker-oriented 82%
  P3 → speaker-oriented 61%
  P4 → possible note-taking 37%

P1 speaking:
  mouth activity: 0.78 · face confidence: 0.93 · speaker attribution confidence: 0.85
```

### 17.4 Stored / API turn (JSON)

```json
{
  "id": "t_0007", "seq": 7, "kind": "TURN",
  "start_ms": 10020, "end_ms": 17950,
  "speaker": {"participant_track_id": "p1…", "speaker_label": "SPEAKER_01", "attribution_confidence": 0.85},
  "speech": {
    "segment_ids": ["s1…"],
    "transcript": "So before we lock the release date, can we check with QA …",
    "asr_confidence": 0.91,
    "prosody": {"f0_mean_hz": 142, "f0_range_semitones": 6.1, "speech_rate_wps": 3.3,
                "articulation_rate_wps": 3.7, "pause_ratio": 0.11, "energy_mean_db": -24.8,
                "baseline_z": {"f0_mean": 0.4, "speech_rate": 0.9}, "reliability": 0.90},
    "linguistic": {"is_question": true, "question_type": "YES_NO", "speech_act": "QUESTION",
                   "sentiment": 0.05}
  },
  "speaker_visual": {"track_id": "p1…", "mouth_activity": 0.78, "face_confidence": 0.93,
                     "visual_coverage": 0.94, "attribution_confidence": 0.85},
  "listeners": [
    {"track_id": "p2…", "top_label": "SPEAKER_ORIENTED", "top_probability": 0.82,
     "label_probs": {"SPEAKER_ORIENTED": 0.82, "NOTE_TAKING": 0.02, "DISTRACTED": 0.06,
                     "NEUTRAL": 0.03, "UNKNOWN": 0.07},
     "display_text": "speaker-oriented 82%", "coverage": 0.96, "reliability": 0.93,
     "counts": {"nods": 1, "gaze_shifts": 2}},
    {"track_id": "p3…", "top_label": "SPEAKER_ORIENTED", "top_probability": 0.61,
     "display_text": "speaker-oriented 61%", "coverage": 0.90, "reliability": 0.87,
     "counts": {"nods": 0, "gaze_shifts": 3}},
    {"track_id": "p4…", "top_label": "NOTE_TAKING", "top_probability": 0.37,
     "label_probs": {"NOTE_TAKING": 0.37, "SPEAKER_ORIENTED": 0.23, "DISTRACTED": 0.18,
                     "NEUTRAL": 0.00, "UNKNOWN": 0.22},
     "display_text": "possible note-taking 37%", "coverage": 0.81, "reliability": 0.78,
     "counts": {"nods": 0, "gaze_shifts": 0}}
  ],
  "events": [
    {"id": "e…1", "type": "QUESTION", "start_ms": 10040, "confidence": 0.75},
    {"id": "e…2", "type": "LISTENER_NOD", "start_ms": 12400, "confidence": 0.71}
  ],
  "overall_confidence": 0.78,
  "coverage": {"audio": 1.0, "video": 0.94},
  "quality_flags": []
}
```

### 17.5 Degraded variant: dropped video 13.0–15.5 s

```
- P2 nod at 12.40 remains (before the gap). Any nod that would fall inside 13.0–15.5 s is NOT
  emitted; nothing is extrapolated (gap 2.5 s ≫ 250 ms max).
- P1 mouth_activity is computed over the remaining valid frames; visual_coverage = 0.94 → 0.63.
- Listener reliability for P2 falls (coverage 0.96 → 0.65): oriented p = 0.65·0.97·0.88 = 0.55,
  shown as "possible speaker-oriented 55%"; UNKNOWN = 0.37.
- DATA_GAP{modality: VIDEO, 13000–15500} event is emitted.
- Turn quality_flags: ["VIDEO_GAP"]; attribution stays 0.85 because it is a cluster-level result
  from the whole meeting (segment-level evidence unavailable, so no override is attempted).
- Transcript, prosody, QUESTION are unchanged: they do not depend on video.
```

---

## 18. Frontend representation

### 18.1 Components (React 18 + TypeScript + Tailwind + Zustand)

| Component | Role |
|---|---|
| `FusionTimelinePage` | Route `/meetings/:id/fusion`. Loads run header + first page of turns |
| `FusionSwimlanes` | Lanes per participant across time: speech blocks, listener-state bands, event ticks. Canvas/SVG, virtualized in time |
| `TurnList` | Virtualized (react-window) list of `TurnCard`s, synced to the playhead |
| `TurnCard` | The text form in §17.3 (transcript, prosody chips, listeners, speaker visual block) |
| `ListenerBadge` | `display_text` + confidence ring + coverage tooltip |
| `ConfidenceMeter` | Small bar; three visual tiers (§9.5), hatched when reliability is low |
| `EventChip` | Event type icon + time; opens the evidence popover |
| `EvidencePopover` | "Why?" view: confidence components, source refs, link to seek the video |
| `SpeakerMapEditor` | Correct label→track mapping; posts to `PUT /fusion/speaker-map` |
| `CoverageStrip` | Per-participant modality coverage with gap marks |

Reuse: `apiClient` (JWT refresh), `useJobPolling` and `JobStatusBadge` for run progress, and the Phase 11 annotated-video `<video>` element as the shared clock.

### 18.2 Types

```ts
export type ListenerLabel = 'SPEAKER_ORIENTED'|'NOTE_TAKING'|'DISTRACTED'|'NEUTRAL'|'UNKNOWN';

export interface ListenerBlock {
  track_id: string;
  top_label: ListenerLabel;
  top_probability: number;
  label_probs: Partial<Record<ListenerLabel, number>>;
  display_text: string;      // server-composed; client never re-derives wording
  coverage: number;
  reliability: number;
  counts: Record<string, number>;
}
export interface FusedTurn { id: string; seq: number; kind: 'TURN'|'GAP';
  start_ms: number; end_ms: number; /* … as §6.2 */ }
```

### 18.3 State (Zustand)

```ts
interface FusionState {
  run?: RunHeader;
  turnsById: Record<string, FusedTurn>;
  order: string[];                          // by seq
  cursor?: string;
  filters: { speakers: string[]; minConfidence: number; showUnreliable: boolean; types: EventType[] };
  playheadMs: number;                       // driven by <video> timeupdate (rAF-throttled)
  activeTurnId?: string;                    // binary search on order by playheadMs
  loadRange(fromMs: number, toMs: number): Promise<void>;   // keyset paging, merges by id
  seek(ms: number): void;                   // sets video.currentTime = ms/1000
}
```

Fetch strategy: initial load of the first ~2 minutes, then range-fetch around the viewport/playhead. Data is merged by `id`, and refetch is invalidated by the run's `ETag`.

### 18.4 Rendering rules

1. **Uncertainty is visible.** Under 0.60 confidence renders with "possible" wording and hatched meters. Under 0.35 it is collapsed, expandable. `UNKNOWN` mass > 0.5 shows "insufficient visual evidence".
2. **Gaps are drawn as gaps.** `DATA_GAP` and low coverage render as hatched segments, never as interpolated lines.
3. **Unattributed speakers** show their diarization label ("Speaker 02 — not matched to a person"), with a one-click mapping action.
4. **Server-composed wording**: `display_text` avoids mind-reading language ("oriented toward speaker", not "was listening").
5. **Time formatting** `mm:ss.mmm` client-side. Uncertainty ±ms in the tooltip.
6. **Accessibility**: percentages are always text (not color-only), lane items keyboard-focusable, and the transcript stays readable at 200% zoom.
7. **Playhead sync**: `timeupdate` at 250 ms, and `requestVideoFrameCallback` when available for the swimlane cursor. Clicking any turn or event calls `seek(start_ms)`.

---

## 19. Performance and scale

| Concern | Approach |
|---|---|
| Volume | The new derived layer is ~10⁴–10⁵ rows per 2-hour meeting. The frame-level data (10⁵–10⁶ rows) is **already** in `feature_extractions` and is not duplicated. |
| Loading CV rows | Stream with server-side cursors / keyset in 60 s chunks. Never load a whole meeting into memory. Signals are resampled to 10 Hz for correlation work |
| Attribution cost | `clusters × tracks × frames` at 10 Hz, trivial (≤ 10×10×72k) |
| Event detection | Windowed (60 s chunks, 5 s overlap, deduped by key) |
| Writes | Batched inserts (5k rows per batch) in one transaction per stage, replace-by-run semantics (doc 16 §9) |
| Reads | Every timeline query is `WHERE fusion_run_id = :r AND start_ms BETWEEN … ORDER BY start_ms, seq LIMIT n`, index-backed |
| Isolation | Dedicated ARQ queue so fusion does not compete with CV/annotation |

---

## 20. Testing and validation

1. **Golden fixtures**: small synthetic meetings (generated audio + scripted mouth/pose tracks) with known ground truth for turns, attribution, nods, and interruptions.
2. **Property tests**: no event exists inside an interval flagged as `DATA_GAP` of its required modality, every interpolated observation is excluded from triggers, timestamps are monotone, and confidences are within [0.01, 0.99].
3. **Fault injection**: randomly drop 10–50% of frames, cut audio ranges, shift audio by ±300 ms, and confirm the clock estimator recovers or degrades with a lower confidence flag rather than a wrong confident answer.
4. **Calibration set**: label 10–20 meetings (speaker map, questions, interruptions, listener states) and fit isotonic calibration per component. Until then the UI wording stays "confidence".
5. **Regression**: snapshot the `FusedTurn` JSON for fixtures; the version bump is intentional.
6. **Idempotence**: a retried ARQ job produces byte-identical rows for the same `input_hash`.

---

## 21. Rollout plan

| Phase | Deliverable | Depends on |
|---|---|---|
| A | Prereqs (§0.3): mouth aperture, `pts_ms`, audio artifact. DB migrations (doc 16). `speech_segments`/`diarization_segments` backfill from current STT output | — |
| B | F0 clock sync + normalization + coverage; `DATA_GAP` events | A |
| C | F3 attribution + `SpeakerMapEditor` | B |
| D | F1/F2 speech analytics; turn assembly; speech events | B |
| E | F4 listeners + interactions | C |
| F | Interaction events (RESPONSE, INTERRUPTION), agreement/disagreement | D, E |
| G | Frontend timeline, evidence popover, video sync | C–F |
| H | Rollups into `behavioral_metrics` and integration into `nts_scores` and LLM report prompts (aggregates only, never raw rows) | F |

## 22. Open questions

1. What capture geometry do real meetings use (room camera vs gallery)? This decides how much of §11 is usable. It is worth sampling 10 meetings before building F4.
2. Is there a name/role map for `ADDRESSEE_MENTION`, or should that event be dropped in v1?
3. Which diarizer is in use, and does it provide overlap-aware output? This affects C6/C7 frequency.
4. Should listener-state labels feed `nts_scores` directly or only via aggregate metrics? I recommend aggregates only, with coverage-weighted means, to avoid scoring people on low-reliability windows.
