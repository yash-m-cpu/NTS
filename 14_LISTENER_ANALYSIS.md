# 14 — Listener Behaviour Analysis

**Project:** NTS Meeting Analysis  **Status:** Design spec (implementation-ready)  **Feature version:** `listener_v1`
**Depends on:** Phase 7 CV extraction (`feature_extractions`), `participant_tracks`, `13_SPEECH_ANALYSIS` (`speech_turns`, `speech_segment_features`, `speech_events`, `speech_dialogue_acts`)
**Feeds:** Phase 10 LLM report ("Attention & Listening" section), annotated video (debug overlay), `nts_scores` fusion (optional)

> **Assumptions to verify against the repo** (written from `project_history_summary.md`, not from the code):
> **B1** `feature_extractions` rows from `human_cv_script.js` include, per frame and per `participant_track_id`: face box + confidence, head rotation (yaw/pitch/roll), gaze bearing/strength, body keypoints (BlazePose), hand detections (± keypoints), emotion scores. Which of these are persisted at what fps must be checked; §3 lists what is required vs. optional.
> **B2** Rows carry a timestamp on the same media clock as STT segments (`t` seconds or `frame_idx/fps`).
> **B3** Head-angle sign conventions of `@vladmandic/human` (what positive yaw/pitch means, degrees vs radians) are verified once on a calibration clip and stored in config (§6.2). **Do not hard-code them from memory.**

---

## 0. Goal, Principles and Vocabulary

**Goal:** for every speaker segment, describe what *the other visible participants* were visibly doing, using signals the platform already extracts, plus a small number of **derived** signals computed from stored rows (no new inference passes unless flagged optional).

**Three strictly separated layers** (every stored value carries `layer`):

| Layer | Meaning | Examples | Stored as |
|---|---|---|---|
| **OBSERVATION** | Directly measured/geometric quantity from CV rows. No psychological meaning. | head yaw error to speaker = 12°, head pitch −22° below own baseline, hand motion energy 0.8 face-heights/s, nod detected (pitch oscillation 5.8°, 2 cycles) | `label_type='observation'` |
| **INFERENCE** | Rule-based, confidence-scored behavioural label combining observations. Uses cautious vocabulary. | `speaker_oriented`, `looking_away`, `possible_note_taking`, `possible_acknowledgment` | `label_type='inference'`, `confidence ∈ [0,1]`, `evidence[]` |
| **INTERPRETATION** | Narrative by the LLM (or a human) about patterns. Never asserts mental states. | "Two of three listeners were mostly oriented toward the presenter." | `nts_listener_reports`, `label_type='interpretation'` |

**Hard rules**

1. **Facing ≠ listening.** No output may state that a person "is listening", "is paying attention", "is bored", "is engaged" as fact. Only the vocabulary below is allowed.
2. **Unknown ≠ away.** If the face/track is not observable, the state is `not_observable` and is excluded from ratios (reported as `coverage`).
3. **Head-down ≠ note-taking.** `possible_note_taking` requires head-down **plus** hand evidence (§8).
4. **Self-relative baselines** for pose (camera mounting biases head pitch/roll).
5. **No individual evaluation.** Metrics are descriptive, shown with confidence and coverage; the composite index is a *measurement of visible behaviour*, not a score of a person.
6. **No parallel tracking system.** All joins use `participant_tracks.id` and read `feature_extractions`; derived per-frame signals are written back to `feature_extractions` with new `feature_type` values.

**Allowed label vocabulary (inference layer)**

| State label | Meaning |
|---|---|
| `speaker_oriented` | head (and, if reliable, gaze) direction is within tolerance of the current speaker's direction |
| `gaze_aligned` | gaze estimate specifically aligned to speaker (subset evidence, stricter) |
| `visually_attentive` | composite: speaker-oriented or shared-focus-oriented, face observable, no distraction evidence (a *pattern label*, still not "listening") |
| `oriented_to_other_person` | direction aligned with a non-speaker participant |
| `oriented_to_shared_focus` | direction aligned with the group's shared focal direction (screen/whiteboard) |
| `looking_away` | observable face, orientation matches no participant and no shared focus |
| `looking_down` | head pitch below own baseline (observation-level posture; no purpose implied) |
| `possible_note_taking` | head-down + writing-like hand motion (+ optional object evidence) |
| `possible_screen_use` | head slightly down/fixed + typing-like bimanual motion and/or laptop detection |
| `possible_phone_use` | head-down + single hand near chest/face + optional phone detection |
| `possible_distraction` | sustained `looking_away`/`possible_phone_use` not explained by shared focus or note-taking |
| `possible_acknowledgment` | nod / thumbs-up / smile-change / brow-raise event temporally coupled to speech |
| `not_observable` | face lost, occluded, off-frame, or low detection confidence |

---

## 1. Integration with Existing Infrastructure

```
cv_extraction ──► feature_extractions (face, pose, hand, emotion, [object])
                          │
speech_analysis (doc 13) ─┼──► speech_turns / speech_segment_features / speech_events / dialogue_acts
                          ▼
              listener_analysis (THIS DOC)  ── ARQ job, cascade after BOTH cv_extraction and speech_analysis succeed
   ├─ 1 load + resample CV signals to a uniform grid (10 Hz)
   ├─ 2 calibrate (per-track baselines, geometry, shared focus)
   ├─ 3 derive per-frame observations → write feature_extractions(feature_type='listener_signals_10hz')
   ├─ 4 detect events (nods, hand activity, gestures)
   ├─ 5 per-frame state inference (multi-label, confidence)
   ├─ 6 align to speaker segments/turns → listener_segment_stats
   ├─ 7 aggregate per listener, per pair (listener→speaker), per meeting
   └─ 8 persist + enqueue llm_report
```

* **Zero re-inference:** exactly like the annotated-video worker, this job reads stored rows only. (Optional Phase-2 extras that require extra CV output are flagged `[CV+]`.)
* **Idempotency key:** `listener_analysis:{meeting_id}:{feature_version}:{config_hash}` (UPSERT on `(meeting_id, feature_version)`); dependency check: requires a finished `speech_analysis` run, else runs with `speech_segments` from Phase 8/9 only and marks `dialogue_act_context=false`.
* **Debug integration:** extend `video_annotation_worker.py` with an optional `overlay=listener` mode that draws each track's current state label + confidence and the speaker's direction arrow, reading `listener_state_runs`. This is the primary human-validation tool (§16).

---

## 2. Scene Modes (critical for what "toward the speaker" means)

Gaze/head orientation only has a geometric meaning if we know what a participant *could* look at.

| Mode | Description | "Toward speaker" is computed by | Reliability |
|---|---|---|---|
| **`room_camera`** | one camera sees several people in the same physical room | 3D-ish geometry from tracked face positions (§6.3) | Good for head, moderate for gaze |
| **`gallery_tiles`** | video-call recording, each participant in own tile, each looking at their own screen | **No geometry exists** between participants. Orientation is measured relative to the *screen/camera direction* only. | Output labels are `screen_oriented` / `looking_away` instead of `speaker_oriented`; speaker-directed metrics = `null` |
| **`mixed`** | hybrid (some in room, some remote) | per-track `scene_group_id`; geometry only within the same group | partial |

`scene_mode` is stored on the meeting (`meetings.settings` or `listener_calibration`) and chosen at upload/config time; auto-detection heuristic: if all face boxes lie inside non-overlapping grid cells of stable size ≥ 95 % of the time → `gallery_tiles`. Everything below assumes `room_camera` unless stated; §6.4 defines the gallery fallback.

---

## 3. Signal Inventory

### 3.1 Existing signals (used as-is)

| Signal | Source row field | Used for |
|---|---|---|
| Face box `(x,y,w,h)`, face confidence | `face` | visibility, distance estimate, geometry, lean |
| Head rotation yaw/pitch/roll | `face.rotation.angle` | orientation, looking down, nods, tilt |
| Gaze bearing & strength | `face.rotation.gaze` | gaze alignment (refining evidence) |
| Body keypoints (BlazePose 33 / MoveNet 17) | `body.keypoints` | shoulders, wrists, torso lean, hand-region |
| Hand detection (± 21 keypoints) | `hand` | hand presence, motion, proximity |
| Emotion scores | `face.emotion` | smile / affect-change events (acknowledgment evidence only) |
| Track identity, lifecycle | `participant_tracks` | joins |
| Speaker segments/turns/acts | doc 13 tables | alignment |

### 3.2 New derived signals (computed from stored rows; no new inference)

`head_yaw_world`, `head_pitch_rel`, `head_roll_rel`, `head_speed`, `nose_y_rel`, `face_scale_rel` (lean), `wrist_y_rel`, `hand_motion_energy`, `hand_dominant_freq`, `hand_extent`, `hand_below_shoulder`, `orientation_target_probs`, `angular_error_to_speaker`, `shared_focus_deviation`.

### 3.3 Optional new raw signals `[CV+]` (feature-flagged, only where the heuristics need them)

| Signal | How | Why |
|---|---|---|
| **Object detections** (`laptop`, `cell phone`, `book`, `keyboard`, `mouse`, `cup`) | enable `human`'s object module (`config.object.enabled=true`, COCO classes) in `human_cv_script.js` behind env `HUMAN_OBJECT_ENABLED`; store as `feature_extractions(feature_type='object_detection', track NULL)`; associate objects to tracks by proximity at analysis time | hand-object proximity, laptop/phone evidence. COCO has no "pen/paper"; `book` is a proxy for notebook. Expect noisy detections → treat as boosting evidence only. |
| **Face mesh lip aperture** | keep mesh landmarks (or just `mouth_open_ratio`) | pre-speech mouth opening for turn preparation |
| **Human gesture module output** | persist coarse gestures (`head up/down`, `brow raise`, `thumb up`, `raised hand`) if the script does not already | acknowledgment gestures |
| **Higher CV fps** | run CV at ≥ 10 fps (5 fps minimum) | nod detection needs ≥ 8–10 fps; below 6 fps nod detection is disabled (`nod_detectable=false`) |

If `[CV+]` signals are absent, the algorithms degrade gracefully: confidence caps apply (§8.4) and the API reports `signals_available`.

---

## 4. Data Structures

```python
@dataclass
class Frame:                        # one row of the uniform 10 Hz grid, per track
    t: float
    track_id: UUID
    observable: bool                # face conf ≥ 0.5 and box inside frame (≥ 80 % visible)
    obs_conf: float                 # 0-1 combined confidence (face conf × pose stability × size factor)
    yaw_w: float | None             # head yaw in camera-world horizontal frame (deg), sign-calibrated
    pitch_rel: float | None         # deg relative to track's baseline (down = negative after calibration)
    roll_rel: float | None
    gaze_err_deg: float | None      # gaze-vs-speaker angular error if gaze reliable
    head_err_deg: float | None      # head-vs-speaker angular error
    target: str | None              # 'speaker' | track_id | 'shared_focus' | 'down' | 'away' | None
    target_probs: dict[str, float]
    hands: HandState                # presence, motion_energy, dominant_freq, extent, below_shoulder, both_hands
    lean_rel: float | None          # log(face_scale / baseline_scale)
    states: dict[str, float]        # state_label -> confidence   (multi-label)
    primary_state: str

@dataclass
class ListenerEvent:                # nods, acknowledgment gestures, hand raises
    track_id: UUID; kind: str; t_start: float; t_end: float
    amplitude: float; n_cycles: int; confidence: float; attrs: dict

@dataclass
class SpeakerInterval:              # from speech_turns (preferred) or speech_segment_features
    id: UUID; speaker_track: UUID; start: float; end: float
    overlap_intervals: list[tuple[float,float]]   # other speakers active
    pauses: list[tuple[float,float]]              # speaker pauses (doc 13)
    acts: list[DialogueAct]

@dataclass
class ListenerSegmentStats:         # one per (speaker_interval, listener_track)
    ...                             # §11/§13
```

Vectorised implementation: per track, numpy arrays on a shared grid `t_k = t0 + k·Δ` (`Δ = 0.1 s`); NaN for missing; `state_conf[track, state, k]` as float32 tensor (`n_tracks × n_states × T`). Interval statistics are then `np.nansum` over slices → O(segments × tracks).

**Resampling rule:** CV rows arrive at irregular/lower fps. Nearest-neighbour to grid with `max_gap = 0.5 s`; beyond that the grid cell is `NaN` (not observable). Never interpolate across gaps for state labels; linear interpolation is allowed only for continuous angles within gaps ≤ 2 frames.

---

## 5. Per-Track Calibration (once per meeting)

Stored in `listener_calibration` (one row per track + one per meeting).

| Item | Method |
|---|---|
| `pitch_baseline_deg` | median head pitch over observable frames where the head is roughly facing a person or the screen (`|yaw_cam| ≤ 25°`); if too few such frames, the 60th percentile of all pitch values (biased toward head-up) |
| `roll_baseline_deg`, `face_scale_baseline` | median over observable frames |
| `jitter_floor_deg` | `1.4826 · MAD(Δ pitch between consecutive frames)`; used as noise floor for nod detection |
| `yaw_sign`, `yaw_offset` | **self-calibration:** for each candidate `(sign ∈ {+1,−1})` compute the mean alignment (§6.3) of all listeners during others' speech; pick the sign with higher mean alignment, require gap ≥ 0.05, else fall back to config default and flag `yaw_sign_uncertain` |
| `focus_direction(t)` (shared focus) | §6.5 |
| `camera_fov_deg`, `real_face_width_m` | config defaults 70° / 0.15 m; used only for relative depth/angle, so errors scale bearings, not orderings |

---

## 6. OBSERVATION Layer — Orientation

### 6.1 Visibility (L08, `face visibility`)
```
observable(t) = face_conf ≥ 0.5 ∧ box fully inside frame (≥ 80 %) ∧ face_width_px ≥ 24 ∧ |yaw_cam| ≤ 75°
visibility_ratio(interval) = observable_time / interval_duration
```
Outputs `obs_conf(t) = face_conf · size_factor · pose_factor`, `size_factor = clip((face_w_px−24)/48, 0.3, 1)`, `pose_factor = 1 − max(0,|yaw_cam|−45)/60`.

### 6.2 Angle conventions
Head angles from `human` are relative to the **camera** (yaw 0 = facing the camera). Convert to a world-horizontal heading using the person's own position so that comparisons between people are meaningful. Sign/units verified via B3 and stored in config.

### 6.3 Direction to speaker (`room_camera`)

Approximate 3D positions from face boxes (pinhole model):
```
Z_i = f_px · W_face / w_i          # depth from face width (W_face = 0.15 m default)
X_i = (x_c,i − c_x) · Z_i / f_px   # lateral position
f_px = (image_w/2) / tan(FOV/2)
```
Bearing from listener L to speaker S in the horizontal plane (camera frame, 0° = along +Z away from camera):
```
β_LS = atan2(X_S − X_L, Z_S − Z_L)
```
Listener's world heading from head yaw: a person facing the camera has heading 180°; turning by `yaw` changes it:
```
heading_L = 180° + yaw_sign · yaw_L + yaw_offset      (wrap to (−180,180])
head_err_LS = |wrap(heading_L − β_LS)|          # angular error in degrees  (L03 / L04)
gaze_err_LS = |wrap(heading_L + gaze_bearing_L − β_LS)| if gaze reliable    (L01)
```
Gaze is *reliable* only if `|yaw_L| ≤ 35°`, iris strength ≥ 0.5 and face width ≥ 60 px; otherwise use head only and mark `gaze_reliable=false`.

**Tolerance** (angular size of the target + pose noise):
```
tol_deg = clip( 12° + degrees(atan(0.10 / D_LS)), 15°, 40° ),   D_LS = √((X_S−X_L)² + (Z_S−Z_L)²)   [metres]
```
`aligned(L→S, t) = head_err ≤ tol` (loose) ; `strict_aligned = head_err ≤ tol/2`; `gaze_aligned = gaze_reliable ∧ gaze_err ≤ tol`.

**Continuous alignment score** used in soft aggregation:
```
a_LS(t) = exp(−½ (head_err / σ)²) , σ = tol/1.5      # in [0,1]
```
Combined orientation score (head primary, gaze refines):
```
s_spk(t) = 0.65·a_head + 0.35·a_gaze     if gaze_reliable
         = a_head                          otherwise
```

**Tier-B lateral fallback** when depth/geometry are unreliable (few tracks, extreme distances, sign uncertainty): use image-space order. Speaker to listener's left/right = `sign(x_S − x_L)`; head turned toward that side if `sign(yaw_sign·yaw) = sign(x_S − x_L)` and `|yaw| ≥ 12°`; near-frontal listeners with speaker directly across are handled by `|Δx| < 0.5·w_face → expected yaw ≈ 0 ± 20°`. Tier-B outputs have confidence multiplied by 0.6.

### 6.4 `gallery_tiles` mode
No inter-person geometry. Compute `screen_orientation = 1 − clip(max(|yaw|,|pitch_rel|)/T, 0, 1)` (T=30°) → states `screen_oriented / looking_away / looking_down / not_observable`. Speaker-directed features L01, L03, L04, L17, cross-person gaze = `null (reason='gallery_mode')`. Hand/note/nod/phone/screen features still apply. Speaker-linked *acknowledgment timing* (L05–L07) remains valid because it is temporal, not spatial.

### 6.5 Shared focus (prevents false "looking away")
When a presenter points at a slide or everyone reads a shared screen, listeners look at the same non-speaker direction.
```
For window W (5 s, hop 1 s): collect heading_L for observable listeners.
Find the mode of headings with a 25°-wide sliding cone; support = share of listeners inside.
shared_focus(W) = mode direction  if support ≥ 0.6 and n_listeners ≥ 3 (or ≥ 2 with both agreeing) and
                  |mode − mean β_L→speaker| > tol.
```
A listener inside the cone gets `oriented_to_shared_focus` (not `looking_away`). Stored in `listener_calibration.focus_windows`.

### 6.6 Target distribution per frame (L17 cross-person gaze)
For each observable listener frame compute `err_j` to every other visible participant j and to `shared_focus`, then a softmax:
```
p(target=j) ∝ exp(−½ (err_j/σ_j)²) · prior(j),  plus  p(down) from pitch_rel,  p(other/away) = residual mass
target = argmax if p_max ≥ 0.45 and margin over 2nd ≥ 0.15 else 'ambiguous'
```
`prior(speaker) = 1.3`, others 1.0 (speaker slightly favoured; corrected in test calibration §16). **Mutual-glance events:** two listeners both `target = each other` for ≥ 0.6 s simultaneously → `side_exchange_candidate` (inference).

---

## 7. OBSERVATION Layer — Motion Signals

### 7.1 Head pitch / looking down (L04, L02 related)
```
pitch_rel(t) = pitch(t) − pitch_baseline          # sign so negative = downwards (after calibration)
head_down(t) = pitch_rel ≤ −θ_down   with θ_down = 15°   (strong)   ; 8°–15° → 'head_tilted_down' weak, weight 0.5
```
Hysteresis: enter at −15°, exit at −10°; minimum run 1.0 s; gap-fill ≤ 0.4 s. Persisted as runs with `mean_pitch_rel`, `duration`.

### 7.2 Nod detection (L05, L06, L07) — `nod_detectable` requires fps ≥ 6
Signals: `pitch_rel(t)` and `nose_y_rel(t) = (nose_y − face_center_y)/face_height` (both if available; agreement raises confidence).
```
1. x(t) = detrend(pitch_rel)            # remove slow drift (Butterworth high-pass 0.4 Hz, zero-phase filtfilt)
2. x_f  = lowpass(x, 4 Hz)              # remove jitter
3. find peaks of −x_f (downward excursions) with prominence ≥ A_min and width 0.1–0.6 s
      A_min = max(4°, 4·jitter_floor_deg)        # nose_y variant: ≥ 3 % face height
4. cycle = downward peak followed by recovery within ≤ 0.8 s (return ≥ 60 % of amplitude)
5. episode = 1–5 cycles with inter-cycle gap ≤ 0.8 s; require peak-to-peak yaw activity < 0.5·pitch amplitude
   (rejects head-shaking / turning), and roll/yaw drift < 8° during episode
6. Exclusions: listener is speaking (doc 13 solo speech of that track) → mark `during_own_speech`, keep but not counted
              body/face jump (box centre shift > 0.4 face-widths in 3 frames) → tracking glitch, discard
7. confidence = sigmoid(0.35·(amp/A_min −1) ) · min(1, n_cycles/2 ·(0.6)+0.4) · obs_conf · (1.0 if both pitch and nose agree else 0.8)
```
Output events: `nod(t_start,t_end,amplitude_deg,n_cycles,freq_hz,confidence)`.
**Nod frequency (L06):** `nod_episodes_per_min = episodes / (observable_speaker_time/60)`; also `nod_cycles`.
**Nod timing relative to speech (L07)** — for each nod, relative to the speaker interval `[s,e]` currently active (with reaction lag `δ = 0.3 s`; a nod at `t` is aligned to speech at `t−δ`):

| Field | Definition |
|---|---|
| `rel_pos` | `(t_nod − s)/(e − s)` ∈ [0,1] |
| `timing_class` | `at_pause` if within ±0.5 s of a speaker pause (doc 13) ≥ 0.3 s; `at_turn_end` if in `[e−0.5, e+1.0]`; `after_dialogue_act` if within 2 s after speaker's `proposal / decision / summary / action_item / question`; `mid_speech` otherwise |
| `latency_to_act_s` | `t_nod − act.end` |

Inference coupling: a nod becomes `possible_acknowledgment` when its confidence ≥ 0.5, it is not `during_own_speech`, and its `timing_class` is `at_pause`, `at_turn_end` or `after_dialogue_act`. Nods classed `mid_speech` stay plain `nod` observations (confidence unchanged, no acknowledgment label).

### 7.3 Hand motion features (L12)
From hand detections (preferred) with body-pose wrists as fallback. Normalise everything by `scale = face_height_px` (or shoulder width), so results are distance-invariant.
```
for each hand h at frame k (require det. conf ≥ 0.5):
    c_h(k) = palm centre (mean of wrist+MCP keypoints, else box centre) / scale
    v_h(k) = ||c_h(k) − c_h(k−1)|| / Δt                    # scale-lengths per second
hand_motion_energy(window) = mean_k v_h(k)                  # 1 s windows, 0.5 s hop
hand_extent(window)        = 95th-pct radius of c_h around window median  # small ⇒ localised motion
hand_dominant_freq         = argmax of Welch PSD of c_h(t) in 1–8 Hz over a 3 s window, plus spectral peakiness = peak/median PSD
hand_below_shoulder        = wrist_y > shoulder_y + 0.3·face_height   (image y down)
hand_presence_ratio        = detected_frames / observable_frames
n_hands_active             = count of hands with motion_energy ≥ 0.15
```
`hand_activity_class(window)`: `still` (E < 0.10), `small_localised` (0.10 ≤ E ≤ 1.5 ∧ extent ≤ 0.6), `large_gesture` (extent > 1.0 ∨ E > 2.5), `hand_raised` (wrist_y < ear_y ∧ vertical velocity up).

Missing hand detection is **not** "no hand movement": hands below the desk/frame are simply unobservable → `hand_observable=false`, which lowers note-taking confidence instead of counting against it (§8.4).

### 7.4 Lean and posture (L20, L21)
`lean_rel(t) = ln(face_w(t)/face_scale_baseline)` (positive ⇒ closer to the camera / leaning in), smoothed 0.5 s; `torso_lean` from shoulder-width change when pose is available; `lean_forward = lean_rel ≥ +0.08` (≈ +8 %) sustained ≥ 0.8 s.

### 7.5 Acknowledgment gesture events (L22)
| Event | Source | Rule |
|---|---|---|
| `nod` | §7.2 | |
| `thumbs_up` / `hand_gesture` | human gesture module `[CV+]` | conf ≥ 0.6, duration ≥ 0.4 s |
| `smile_shift` | emotion `happy` probability | rises ≥ +0.25 over own baseline within 1 s and holds ≥ 0.5 s (affect model accuracy is limited: evidence only, weight 0.4) |
| `brow_raise` | face gesture `[CV+]` | ≥ 0.3 s |
| `head_tilt` | `roll_rel` | `|roll_rel| ≥ 10°` sustained ≥ 1 s (weak evidence) |

---

## 8. INFERENCE Layer — Per-Frame State Detection

All states are computed on a 1 s sliding evidence window (0.5 s hop) then written per grid frame. Evidence values are in `[0,1]`; confidence combines **evidence strength** and **evidence coverage** (how many required signals were observable).

### 8.1 Generic scoring
```
score  = Π_gates(g) · Σ_i w_i · e_i / Σ_i w_i          # gates are hard necessary conditions (0/1 or soft ramps)
coverage = Σ_i w_i·1[e_i observable] / Σ_i w_i
conf   = score · (0.4 + 0.6·coverage) · obs_conf_mean
```
No trained weights exist yet → weights below are hand-set priors and must be **calibrated** with §16.

### 8.2 Speaker-oriented family (L01–L04, L09)
```
speaker_oriented(t)  = s_spk(t) ≥ 0.6    (soft score s_spk; conf = s_spk · obs_conf)
looking_away(t)      = observable ∧ max_j p(target=j) < 0.45 ∧ p(down) < 0.4 ∧ not shared_focus ∧ head_err_to_all > tol
looking_down(t)      = head_down(t)
attention_orientation(t) ∈ {speaker, other_person, shared_focus, down, away, not_observable}    (= L09)
```
Runs are smoothed with median filter 0.5 s, min run 0.6 s, gap-fill 0.4 s.

### 8.3 Note-taking-like behaviour (L10, L13, L14) — `possible_note_taking`

**Gates (all must hold on ≥ 70 % of the window, otherwise score = 0):**
G1 `head_down` (pitch_rel ≤ −θ_down) — *necessary, never sufficient*
G2 face observable ≥ 60 %
G3 window ≥ 3 s (state needs sustained evidence; runs shorter than 3 s are not labelled)

**Evidence terms (weights sum to 1):**

| e_i | Definition | w |
|---|---|---|
| `e_hand_present` | hand in lower frame region (`hand_below_shoulder`) and detected | 0.15 |
| `e_hand_motion` | `hand_activity_class = small_localised` fraction of window (motion energy within 0.10–1.5) | 0.25 |
| `e_repetitive` | `hand_dominant_freq ∈ [1.5, 6] Hz` and spectral peakiness ≥ 3, **or** ≥ 3 direction reversals/s | 0.20 |
| `e_unimanual` | one hand active (`n_hands_active = 1`) — writing; two synchronous active hands suggests typing | 0.10 |
| `e_object` `[CV+]` | hand within 1.0·face_h of `book`/paper-like bbox that lies in lower region | 0.15 |
| `e_posture` | head pitch stable (std over window ≤ 6°) and slight forward lean (`lean_rel ≥ 0`), shoulders roughly level | 0.10 |
| `e_duration` | ramp: `clip((run_duration − 3 s)/12 s, 0, 1)` | 0.05 |

**Negative evidence (multiplicative penalties):** `hand_activity_class=large_gesture` → ×0.3; hand raised → ×0; two hands synchronously active with mid-frame keyboard/laptop detection → ×0.4 (goes to `possible_screen_use`); hand near face/holding phone-like pose → ×0.4.
**Confidence cap without hand observability:** if `hand_observable < 30 %` the state is **not** emitted (only `looking_down` remains). If `[CV+]` object detection is off, confidence is capped at **0.7**; with object detection supporting evidence cap 0.9.
**Emit** when `conf ≥ 0.45` (`possible_note_taking`), `≥ 0.7` marks `likely` in the UI, still worded "possible".

**Explicit non-claims:** head-down alone → `looking_down` only; head-down + still hands → `looking_down` (state may become `possible_phone_use`/`possible_screen_use` if their evidence fits, else nothing more).

### 8.4 Screen and phone (L15/L16 → `possible_screen_use`, `possible_phone_use`)

| State | Gates | Positive evidence (examples of weights) | Discriminator |
|---|---|---|---|
| `possible_screen_use` (looking at laptop/screen) | observable; pitch_rel between −8° and −25°; head yaw within ±20° of camera-forward; sustained ≥ 4 s | bimanual synchronous small motion 1.5–8 Hz (0.3), hands low & symmetric (0.15), `laptop`/`keyboard` object near (0.25), gaze strength downward-frontal (0.15), stable head (0.15) | in `room_camera`, a person looking at a laptop is distinguishable from note-taking by *both* hands active and object evidence; in `gallery_tiles` this is the *default* posture and is **not** labelled distraction |
| `possible_phone_use` | pitch_rel ≤ −12°; sustained ≥ 5 s; not in note-taking state | one hand at chest/face height, low extent (0.25), thumb-scroll micro-motion / `cell phone` bbox overlapping hand (0.35), other hand still (0.15), head static (0.15), no pen-like repetitive motion (0.10) | confidence cap 0.5 without `[CV+]` object detection |

### 8.5 Distraction (L18) — `possible_distraction`
```
candidate run = (looking_away ∨ possible_phone_use) with duration ≥ 4 s, gap-fill ≤ 1.5 s
exclude if within shared_focus window, or state ∈ {possible_note_taking, possible_screen_use (gallery mode)}, or track not observable > 30 %
conf = mean(run.state_conf) · min(1, duration/10 s) · (1 − uncertainty_penalty)
emit if conf ≥ 0.5;  report: count, total_s, longest_s, share of speaker time
```
Attaches `explained_by` if a plausible benign explanation is present (shared focus, note-taking, someone else speaking to them: `oriented_to_other_person`).

### 8.6 Engagement-duration runs (L19)
`visually_attentive(t)` = `speaker_oriented ∨ oriented_to_shared_focus ∨ possible_note_taking(conf≥0.6)` and no distraction/phone flag and observable. Then:
* `visual_attention_time_s` = Σ duration (confidence-weighted variant: Σ conf·Δt),
* `longest_sustained_run_s` (gap tolerance 1.0 s, so blinking/glances don't split runs),
* `attention_break_count` (transitions out of state, runs ≥ 0.6 s),
* `mean_break_duration_s`.

### 8.7 Response readiness & turn preparation (L20, L21)

Two related but distinct quantities:

**(a) Response readiness (INFERENCE, prospective; computed at every frame during others' speech)**
```
rr(t) = 0.30·e_orient + 0.25·e_lean + 0.20·e_hand_raise + 0.15·e_head_up_recover + 0.10·e_mouth[CV+]
  e_orient        = s_spk(t) smoothed over 2 s (sustained orientation)
  e_lean          = clip((lean_rel − 0.03)/0.10, 0, 1)
  e_hand_raise    = 1 if hand_raised ≥ 0.4 s else 0
  e_head_up_recover = 1 if head_down run ended within the last 2 s and head now oriented (person "surfaced")
  e_mouth         = mouth_open_ratio rise above own baseline (only if mesh stored)
```
`readiness_peak` per (listener, speaker-interval) = max over the last 3 s of the interval; `readiness_flag = rr ≥ 0.6 for ≥ 1 s`. Wording: **"possible response readiness"**.

**(b) Turn-preparation behaviour (OBSERVATION of what preceded actual turns)**
For each turn onset of listener L at `t0` (from `speech_turns`), analyse window `[t0 − 3 s, t0]`: whether L was `speaker_oriented`, `lean_forward` onset time, `head_down → head_up` transition, hand raised, presence of `nod`, gaze shift to current speaker. Produces `turn_prep_profile(L)`: fraction of L's turns preceded by each cue, median cue lead-time. These profiles are **observations about past turns**, the safest evidence for interpretation.

**Validation trick (no manual labels needed):** treat "next speaker" as pseudo-ground-truth and evaluate `readiness_peak` as a predictor: AUC over all speaker intervals for (listener speaks next vs. not). Report the AUC in run quality; tune weights to maximise it. If AUC < 0.55 the readiness feature is hidden by default.

---

## 9. OBSERVATION → INFERENCE → INTERPRETATION Summary Table

| # | Feature (task item) | OBSERVATION (stored, measurable) | INFERENCE (label, cautious) | INTERPRETATION (LLM only) |
|---|---|---|---|---|
| L01 | Speaker-directed gaze | `gaze_err_deg`, `gaze_reliable`, ratio of frames within tol | `gaze_aligned` (conf) | "Listener B's eyes were often directed toward the speaker." (never "was listening") |
| L02 | Gaze-away duration | seconds/runs where target ≠ speaker & observable | `looking_away` | pattern statements only |
| L03 | Head toward speaker | `head_err_deg` mean, % within tol | `speaker_oriented` | |
| L04 | Head away from speaker | % beyond tol, `yaw_w` distribution | `looking_away`, `oriented_to_other_person` | |
| L05 | Nodding | nod events (amplitude, cycles) | `possible_acknowledgment` (with timing) | |
| L06 | Nod frequency | episodes/min, cycles | – | |
| L07 | Nod timing | `rel_pos`, `timing_class`, latency | coupled to dialogue acts | |
| L08 | Face visibility | `visibility_ratio` | `not_observable` | |
| L09 | Attention orientation | target distribution over interval | `attention_orientation` class | |
| L10 | Looking at notes | head-down + downward gaze | `looking_down`; with hands → `possible_note_taking` | |
| L11 | Looking down | `pitch_rel`, run durations | `looking_down` | |
| L12 | Hand movement | motion energy, extent, dominant freq, activity class | `hand_activity_class` | |
| L13 | Note-taking-like | evidence terms e_i | `possible_note_taking` (conf) | |
| L14 | Writing posture | head pitch stability, lean, hand below shoulder | evidence input to L13 | |
| L15 | Laptop/screen | pitch band, bimanual motion, object bbox | `possible_screen_use` | |
| L16 | Phone | single-hand chest pose, object bbox | `possible_phone_use` | |
| L17 | Cross-person gaze | `target_probs`, mutual-glance events | `oriented_to_other_person`, `side_exchange_candidate` | |
| L18 | Distracted periods | run lengths of away/phone states | `possible_distraction` | |
| L19 | Engagement duration | runs of `visually_attentive` | – | |
| L20 | Response readiness | lean, hand-raise, orientation, head-up signals | `possible_response_readiness` | |
| L21 | Turn preparation | cue presence in 3 s before real turns | `turn_prep_profile` | |
| L22 | Visible acknowledgment gestures | nod/gesture/smile-shift/brow events | `possible_acknowledgment` | |

### 9.1 Composite Observable Engagement Index (OEI)

A **measurement composite of visible behaviour** (not psychological engagement). Range 0–100 with `oei_confidence`.

For listener L over interval I (speaker segment, turn, window, or whole meeting, excluding self-speaking time):
```
Let O = observable time in I;   coverage = O/|I|
A = Σ conf·1[speaker_oriented ∨ oriented_to_shared_focus]·Δt / O                # orientation share
K = min(1, nod_episodes_per_min / 6)                                            # acknowledgment, saturating; 6/min = full credit
N = Σ conf·1[possible_note_taking]·Δt / O                                       # content-directed activity (partial credit)
D = Σ conf·1[possible_distraction ∨ possible_phone_use ∨ looking_away_unexplained]·Δt / O
R = mean(readiness_flag)                                                        # optional, small
OEI_raw = 100 · clip( 0.55·A + 0.15·K + 0.15·(0.6·N) + 0.05·R + 0.10·(1 − D) − 0.30·D , 0, 1 )
OEI = OEI_raw · gate(coverage)       gate = 0 if coverage < 0.4 else 1     # not reported when mostly unobservable
oei_confidence = coverage · mean(obs_conf) · min(1, |I|/10 s)
```
Rules: the overlap between `A` and `N` is removed (note-taking frames are counted once, in N, if not also speaker-oriented); components are stored so the UI can show the breakdown; intervals < 3 s produce `null`; the meeting-level OEI is the duration-weighted mean over the listener's non-speaking intervals. **Never rank individuals by OEI in UI defaults**; show distributions and group-level summaries; display `coverage` and `oei_confidence` beside every value.

---

## 10. Alignment of Listener Features with Speaker Segments

### 10.1 Rule set

1. **Clock:** CV frames and STT share the media clock (B2). If an A/V offset `Δav` is configured (measured on clap/sync clip), shift speech times by `+Δav` once at load.
2. **Unit of alignment:** `speech_turns` (default). Turns ≥ 3 s → full statistics; 1–3 s → `low_support=true` (stored, excluded from person-level ratios unless pooled); < 1 s (backchannels) → ignored as speaker intervals but recorded as speaker-context for nods.
3. **Effective interval:** `E = [s − pre, e + post]` with `pre = 0.5 s` (captures orienting toward the incoming speaker) and `post = 0.5 s`; **statistics use the core `[s, e]`**; the pre/post margins are used only for `orientation_latency` and reaction-lag nod matching.
4. **Frames in scope:** listener grid frames with `t ∈ [s, e]` and `solo_or_dominant(t) = speaker` — frames where another speaker is simultaneously active (doc 13 `overlap(t)`) are **excluded** from ratios (counted in `overlap_frames_excluded`). Frames where the listener is himself/herself speaking are excluded (`self_speaking_frames`).
5. **Who are listeners:** all tracks in `participant_tracks` alive during the interval (track `first_seen ≤ e ∧ last_seen ≥ s`) except the speaker. A track alive but not observable is included with `coverage` low; a track outside its lifespan is omitted.
6. **Weights:** each frame k has duration `d_k = min(t_{k+1} − t_k, max_gap)`; ratios use only observable frames as denominator:
```
T_obs(L, I)      = Σ_k∈I d_k · 1[observable]
ratio(state)     = Σ_k∈I d_k · 1[observable] · 1[state at k] / T_obs
ratio_conf(state)= Σ_k d_k · observable · conf_k(state) / T_obs      # soft, confidence-weighted variant (both stored)
coverage         = T_obs / (|I| − excluded_time)
```
7. **Long segments:** intervals > 30 s additionally get sub-windows (10 s, hop 5 s) for timelines.
8. **Nested labels:** `looking_down ⊇ possible_note_taking` and `looking_down ⊇ possible_phone_use`; ratios need not sum to 1. Additionally store a **mutually exclusive `primary_state` distribution** (priority: `possible_note_taking > possible_phone_use > possible_screen_use > looking_down > oriented_to_shared_focus > speaker_oriented > oriented_to_other_person > looking_away > not_observable`) that sums to 1.
9. **Events** (nods etc.) are assigned to the speaker interval containing `t − δ` (δ = 0.3 s reaction lag); events straddling turns use their start.
10. **Orientation latency:** `first t ≥ s−0.5 s` with `speaker_oriented` for ≥ 0.4 s minus `s` (null if never oriented within 3 s).
11. **Speaker-context inclusion:** attach the speaker's pause list, dialogue acts and `ends_with_question` (doc 13) so nod timing and `response_readiness` can be interpreted in context.

### 10.2 Worked example (matches the specification)

Speaker **A** speaks from **120.0 s to 132.5 s** (12.5 s), CV grid 10 Hz ⇒ 125 frames, no simultaneous speech.

| Listener | Frames in scope | Observable frames | Coverage | Frames in state | Ratio (of observable) | Reported |
|---|---|---|---|---|---|---|
| **B** | 125 | 120 | 0.96 | 97 `speaker_oriented` | 97/120 = **0.81** | gaze/head toward A = **81 %** |
| **C** | 125 | 118 | 0.94 | 73 `speaker_oriented` | 73/118 = **0.62** | toward A = **62 %** |
| **D** | 125 | 121 | 0.97 | 54 `looking_down`; 38 of them `possible_note_taking` | 54/121 = **0.45**; 38/121 = **0.31** | looking down = **45 %**, possible note-taking = **31 %** |

Reading the table: D's 31 % note-taking-like frames are a **subset** of the 45 % head-down frames (the remaining 16 % is head-down without sufficient hand evidence → labelled only `looking_down`). B and C percentages are ratios of *observable* time, so C's 62 % does not treat the 7 lost frames as "away". The primary-state distribution for D might read: note_taking 31 %, looking_down (no hand evidence) 14 %, speaker_oriented 42 %, looking_away 8 %, not_observable stored separately (3 %).

Generated record (abridged):
```json
{
 "speaker_interval": {"id": "turn_17", "speaker_track_id": "A", "start": 120.0, "end": 132.5, "duration": 12.5,
                      "overlap_frames_excluded": 0, "acts": ["proposal"], "pauses": [[125.4,125.9]]},
 "listeners": [
  {"track_id": "B", "coverage": 0.96, "oei": {"value": 78.0, "confidence": 0.84, "components": {"A":0.81,"K":0.33,"N":0.0,"D":0.02}},
   "states": {"speaker_oriented": {"ratio": 0.81, "ratio_conf_weighted": 0.74, "label_type": "inference"}},
   "gaze": {"gaze_aligned_ratio": 0.70, "gaze_reliable_ratio": 0.66},
   "nods": [{"t": 124.7, "timing_class": "at_pause", "confidence": 0.68}], "orientation_latency_s": 0.4},
  {"track_id": "C", "coverage": 0.94, "states": {"speaker_oriented": {"ratio": 0.62}}, "away_runs": [{"start":128.1,"end":130.4,"target":"oriented_to_other_person:D"}]},
  {"track_id": "D", "coverage": 0.97,
   "states": {"looking_down": {"ratio": 0.45, "label_type": "observation"},
              "possible_note_taking": {"ratio": 0.31, "confidence_mean": 0.63, "label_type": "inference",
                                       "evidence": ["head_down","small_localised_hand_motion","unimanual"], "caps": ["no_object_detection"]}}}
 ]
}
```

### 10.3 Aggregation ladder
1. **Segment × listener** (`listener_segment_stats`) – as above.
2. **Listener × speaker (pair)** – duration-weighted over all intervals where that speaker spoke: `pair_speaker_oriented_ratio[L→S]`, nods per minute of S's speech, etc. (answers "who attends to whom").
3. **Listener (meeting)** – over all non-self intervals.
4. **Speaker "audience view"** – for each speaker, distribution over listeners of orientation/away/nod stats (`audience_summary`): mean, min–max, count of listeners `visually_attentive ≥ 0.6`. Descriptive, not a speaker-quality score.
5. **Meeting** – attention share over time (30 s windows), synchrony events (≥ 60 % of observable listeners shift orientation to same target within 1.5 s — `joint_attention_shift`), distraction density, nod density near decisions/proposals.

---

## 11. Algorithms in Pseudocode

```python
async def listener_analysis_worker(ctx, meeting_id, config):
    run = start_run(meeting_id, config)
    tracks = load_participant_tracks(meeting_id)
    rows   = load_feature_extractions(meeting_id, types=['face','body','hand','emotion','object_detection'])
    grid   = resample_to_grid(rows, dt=0.1, max_gap=0.5)                        # §4
    turns  = load_speech_turns(meeting_id); acts, pauses = load_speech_context(meeting_id)
    calib  = calibrate(grid, turns, tracks, config)                             # §5 incl. yaw sign, baselines, focus windows
    sig    = derive_signals(grid, calib)                                        # §6-7 (vectorised)
    persist_signals(sig)                                                        # feature_extractions('listener_signals_10hz')
    events = detect_events(sig, calib, turns)                                   # nods, gestures, hand raises, side exchanges
    states = infer_states(sig, events, calib, config)                           # §8, multi-label tensor + primary_state
    runs   = states_to_runs(states, min_len=config.min_run)                     # run-length encoding
    seg_stats = []
    for I in turns:
        for L in listeners_alive(tracks, I):
            seg_stats.append(align_and_aggregate(L, I, states, events, sig, acts, pauses))   # §10
    pair, listener, speaker_view, meeting = aggregate_ladder(seg_stats, states)
    oei = compute_oei(seg_stats, listener)                                       # §9.1
    rr_auc = validate_readiness(seg_stats, turns)                                # §8.7
    persist_all(run, runs, events, seg_stats, pair, listener, meeting, oei, quality={'rr_auc': rr_auc, ...})
    enqueue_next(meeting_id, 'llm_report')
```

**Segment alignment core**
```python
def align_and_aggregate(L, I, S, events, sig, acts, pauses, cfg):
    s, e = I.start, I.end
    idx = grid_slice(s, e)
    excl = sig.overlap_mask[idx] | sig.self_speaking[L][idx]
    obs  = sig.observable[L][idx] & ~excl
    d    = sig.dt * obs
    T_obs = d.sum(); cov = T_obs / max(1e-6, (e - s) - sig.dt * excl.sum())
    out = {'coverage': cov, 'T_obs': T_obs}
    if T_obs < cfg.min_obs_s:            # e.g. 1.5 s
        return mark_low_support(out)
    for state in STATES:
        m  = S.mask[L][state][idx]                     # bool
        c  = S.conf[L][state][idx]                     # float
        out[state] = {'ratio': (d*m).sum()/T_obs, 'ratio_conf': (d*c).sum()/T_obs,
                      'seconds': (d*m).sum(), 'longest_run_s': longest_run(m & obs, sig.dt)}
    out['primary_dist'] = primary_state_distribution(S.primary[L][idx], obs, sig.dt)
    out['head_err_mean'] = nanmean(sig.head_err[L][idx][obs]); out['within_tol'] = ...
    out['nods'] = [attach_timing(n, I, pauses, acts, cfg.reaction_lag) for n in events.nods_in(L, s+cfg.lag, e+cfg.lag)]
    out['nod_rate_per_min'] = len(out['nods']) / (T_obs/60) if T_obs >= 5 else None
    out['orientation_latency_s'] = first_oriented_latency(S, L, s, cfg.pre_margin)
    out['away_runs']       = runs_where(S.primary[L][idx] == 'looking_away', min_len=1.0)
    out['readiness_peak']  = max_last_seconds(sig.rr[L], e, 3.0)
    out['oei'] = oei_interval(out)
    return out
```

**Nod detector**
```python
def detect_nods(pitch_rel, nose_y, dt, jitter, own_speech_mask):
    if 1/dt < 6: return [], 'nod_detectable=False'
    x = filtfilt(*butter(2, [0.4, 4.0], btype='band', fs=1/dt), fill_short_nans(pitch_rel))
    A_min = max(4.0, 4*jitter)
    peaks, props = find_peaks(-x, prominence=A_min, width=(0.1/dt, 0.6/dt))
    cycles = [p for p in peaks if recovers(x, p, frac=0.6, within=0.8/dt)]
    episodes = group_cycles(cycles, max_gap=0.8/dt, max_cycles=5)
    out = []
    for ep in episodes:
        if yaw_activity(ep) > 0.5*amp(ep) or glitch(ep): continue
        conf = nod_confidence(ep, nose_y_agree(ep), obs_conf(ep))
        out.append(Nod(ep.t0, ep.t1, amp(ep), len(ep.cycles), conf, during_own_speech=own_speech_mask[ep.slice].any()))
    return out, None
```

**Note-taking scorer**
```python
def note_taking_score(win):                              # win = 1-3 s+ evidence window (run-based, ≥ 3 s)
    if win.head_down_frac < 0.7 or win.observable_frac < 0.6 or win.duration < 3.0: return 0.0, {}
    if win.hand_observable_frac < 0.3: return 0.0, {'reason': 'hands_not_observable'}
    e = dict(hand_present=win.hand_below_shoulder_frac,
             hand_motion=win.frac_class('small_localised'),
             repetitive=float(1.5 <= win.hand_freq <= 6 and win.peakiness >= 3 or win.reversals_per_s >= 3),
             unimanual=float(win.n_hands_active == 1),
             obj=win.obj_paper_near_hand if win.has_objects else None,
             posture=float(win.pitch_std <= 6 and win.lean_rel >= 0),
             duration=clip((win.duration - 3)/12, 0, 1))
    w = dict(hand_present=.15, hand_motion=.25, repetitive=.20, unimanual=.10, obj=.15, posture=.10, duration=.05)
    used = {k: v for k, v in e.items() if v is not None}
    score = sum(w[k]*used[k] for k in used) / sum(w[k] for k in used)
    cov   = sum(w[k] for k in used) / sum(w.values())
    penalty = 0.3 if win.frac_class('large_gesture') > .3 else 1.0
    if win.bimanual_sync and win.laptop_near: penalty *= 0.4
    conf = score * penalty * (0.4 + 0.6*cov) * win.obs_conf
    conf = min(conf, 0.9 if win.has_objects else 0.7)
    return conf, e
```

---

## 12. Thresholds and Defaults (`listener_config.yaml`)

| Key | Default | Notes / rationale |
|---|---|---|
| `grid_dt_s` / `max_gap_s` | 0.1 / 0.5 | |
| `observable.face_conf_min` | 0.5 | |
| `observable.face_w_px_min` | 24 | below this, angles are noise |
| `observable.max_abs_yaw_cam_deg` | 75 | |
| `orient.tol_min/max_deg` | 15 / 40 | distance-scaled §6.3 |
| `orient.speaker_oriented_score` | 0.6 | |
| `gaze.reliable_max_yaw_deg`, `strength_min` | 35, 0.5 | |
| `pitch.down_enter/exit_deg` | −15 / −10 | hysteresis, relative to baseline |
| `pitch.down_weak_deg` | −8 | |
| `min_run_s.state` / `gap_fill_s` | 0.6 / 0.4 | |
| `note.min_duration_s` | 3.0 | |
| `note.emit_conf` / `cap_no_object` / `cap_object` | 0.45 / 0.7 / 0.9 | |
| `hand.motion_still_max` | 0.10 scale-lengths/s | |
| `hand.small_localised_range` | 0.10–1.5, extent ≤ 0.6 | |
| `hand.large_gesture_extent` / `energy` | > 1.0 / > 2.5 | |
| `hand.writing_freq_hz` | 1.5–6 | |
| `nod.fps_min` / `amp_min_deg` / `jitter_k` | 6 / 4 / 4 | |
| `nod.cycle_recovery_s` / `episode_gap_s` | 0.8 / 0.8 | |
| `nod.reaction_lag_s` | 0.3 | |
| `phone.min_duration_s` / `screen.min_duration_s` | 5 / 4 | |
| `distraction.min_duration_s` / `emit_conf` | 4 / 0.5 | |
| `shared_focus.cone_deg` / `support` / `window_s` | 25 / 0.6 / 5 | |
| `lean.forward_threshold` | +0.08 ln-scale (~8 %) sustained 0.8 s | |
| `segment.min_full_stats_s` / `min_obs_s` | 3.0 / 1.5 | |
| `pre_margin_s` / `post_margin_s` | 0.5 / 0.5 | |
| `oei.weights` | A .55, K .15, N .15(×0.6), R .05, (1−D) .10, D −.30 | provisional |
| `oei.min_coverage` | 0.4 | |

All are hashed into `config_hash`. **All numeric thresholds are priors, not validated constants;** §16 defines the calibration loop.

---

## 13. Database Schema Requirements

New Alembic migration `add_listener_analysis`. Joins use existing `participant_tracks(id)` and `meetings(id)`; RLS via `organization_id`.

```sql
CREATE TABLE listener_analysis_runs (
  id UUID PRIMARY KEY, meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL, feature_version TEXT NOT NULL, config_hash TEXT NOT NULL, config JSONB NOT NULL,
  scene_mode TEXT NOT NULL,                     -- room_camera | gallery_tiles | mixed
  signals_available JSONB,                      -- {"hands":true,"objects":false,"gesture":false,"fps":10,"nod_detectable":true}
  quality JSONB,                                -- coverage stats, yaw_sign_uncertain, readiness_auc, warnings[]
  status TEXT, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
  UNIQUE (meeting_id, feature_version)
);

CREATE TABLE listener_calibration (
  run_id UUID REFERENCES listener_analysis_runs(id) ON DELETE CASCADE,
  participant_track_id UUID REFERENCES participant_tracks(id),   -- NULL row = meeting-level geometry
  pitch_baseline_deg REAL, roll_baseline_deg REAL, face_scale_baseline REAL, jitter_floor_deg REAL,
  yaw_sign SMALLINT, yaw_offset_deg REAL, scene_group_id TEXT,
  geometry JSONB,                               -- fov, real_face_width, per-track median position
  focus_windows JSONB,                          -- [{t0,t1,direction_deg,support}]
  PRIMARY KEY (run_id, participant_track_id)
);

-- Derived per-frame signals go through the existing infrastructure:
--   feature_extractions(feature_type='listener_signals_10hz', participant_track_id, t_start, t_end, payload JSONB)
--   payload = {dt:0.1, observable:[...], obs_conf:[...], yaw_w:[...], pitch_rel:[...], head_err:[...],
--              gaze_err:[...], hand_energy:[...], hand_class:[...], lean_rel:[...], target:[...]}
-- and optional feature_extractions(feature_type='object_detection', participant_track_id NULL).

CREATE TABLE listener_state_runs (               -- run-length encoded inference states (compact; drives timeline + video overlay)
  id BIGSERIAL PRIMARY KEY, run_id UUID, participant_track_id UUID, state TEXT,
  t_start REAL, t_end REAL, duration REAL GENERATED ALWAYS AS (t_end - t_start) STORED,
  confidence REAL, mean_obs_conf REAL, label_type TEXT,           -- 'observation' | 'inference'
  target_track_id UUID NULL, evidence JSONB, caps JSONB           -- e.g. ["no_object_detection"]
);
CREATE INDEX ON listener_state_runs (run_id, participant_track_id, t_start);

CREATE TABLE listener_events (                   -- nods, gestures, hand raises, side exchanges, joint attention shifts
  id BIGSERIAL PRIMARY KEY, run_id UUID, participant_track_id UUID, event_type TEXT,
  t_start REAL, t_end REAL, confidence REAL, label_type TEXT,
  speaker_track_id UUID, speaker_turn_id UUID, timing_class TEXT, rel_pos REAL, latency_to_act_s REAL,
  attributes JSONB                               -- amplitude_deg, n_cycles, freq_hz, during_own_speech, act
);
CREATE INDEX ON listener_events (run_id, event_type, t_start);

CREATE TABLE listener_segment_stats (            -- one row per (speaker turn, listener)
  run_id UUID, speaker_turn_id UUID REFERENCES speech_turns(id), speaker_track_id UUID,
  listener_track_id UUID REFERENCES participant_tracks(id),
  start_time REAL, end_time REAL, duration REAL, coverage REAL, observable_s REAL,
  low_support BOOL, overlap_excluded_s REAL, self_speaking_excluded_s REAL,
  speaker_oriented_ratio REAL, looking_away_ratio REAL, looking_down_ratio REAL,
  possible_note_taking_ratio REAL, possible_screen_use_ratio REAL, possible_phone_use_ratio REAL,
  shared_focus_ratio REAL, other_person_ratio REAL,
  gaze_aligned_ratio REAL, head_err_mean_deg REAL, orientation_latency_s REAL,
  nod_count INT, nod_rate_per_min REAL, ack_event_count INT, hand_motion_mean REAL, readiness_peak REAL,
  longest_oriented_run_s REAL, away_run_count INT, distraction_flag BOOL,
  oei REAL, oei_confidence REAL, oei_components JSONB,
  primary_state_dist JSONB, states JSONB,        -- full ratio/ratio_conf/seconds/longest_run per state
  PRIMARY KEY (run_id, speaker_turn_id, listener_track_id)
);
CREATE INDEX ON listener_segment_stats (run_id, listener_track_id);

CREATE TABLE listener_pair_stats (run_id UUID, listener_track_id UUID, speaker_track_id UUID,
  speaker_time_s REAL, observable_s REAL, speaker_oriented_ratio REAL, gaze_aligned_ratio REAL,
  nod_rate_per_min REAL, metrics JSONB, PRIMARY KEY (run_id, listener_track_id, speaker_track_id));

CREATE TABLE listener_meeting_stats (            -- per listener + meeting scope (participant_track_id NULL = meeting)
  run_id UUID, participant_track_id UUID, coverage REAL, oei REAL, oei_confidence REAL,
  visual_attention_time_s REAL, longest_sustained_run_s REAL, attention_break_count INT,
  distraction_count INT, distraction_total_s REAL, nod_episodes INT, nod_rate_per_min REAL,
  turn_prep_profile JSONB, metrics JSONB, timeline JSONB,
  PRIMARY KEY (run_id, participant_track_id)
);

CREATE TABLE nts_listener_reports (meeting_id UUID, run_id UUID, model TEXT, prompt_hash TEXT, report JSONB, PRIMARY KEY (meeting_id, prompt_hash));
```
Also write headline numbers into `behavioral_metrics` (`metric_family='listener'`, e.g. `speaker_oriented_ratio`, `nod_rate`, `oei`) so `nts_scores` fusion and existing dashboards keep working.

---

## 14. API

Base `/api/v1/meetings/{meeting_id}/listeners` (JWT + RBAC as in `04_API_AUTH`; `POST /run` for `ANALYST+`).

| Endpoint | Returns |
|---|---|
| `POST /run` | enqueue (idempotent, `force`) → `{job_id}` |
| `GET /summary` | run quality, `signals_available`, per-listener meeting stats, group-level summary |
| `GET /segments/{turn_id}` | the aligned record for one speaker turn (§10.2 format) |
| `GET /matrix` | `listener × speaker` `speaker_oriented_ratio`, nod rate, with `observable_s` |
| `GET /timeline?track_id=&from=&to=` | state runs + events (for swimlane) |
| `GET /events?type=nod,possible_distraction,side_exchange_candidate` | event list |
| `GET /attention-series?bucket=30` | share of observable listeners in each state per window + shared-focus windows |
| `GET /calibration` | baselines and geometry (for debugging) |
| `GET/POST /report` | LLM interpretation |

Value envelope (same as doc 13): `{value, unit, layer, label_type, confidence?, coverage?, n?, evidence?, caps?, caveats?}`. Example (meeting summary excerpt):
```json
{
 "run": {"scene_mode": "room_camera", "signals_available": {"hands": true, "objects": false, "nod_detectable": true, "fps": 10},
         "quality": {"yaw_sign_uncertain": false, "readiness_auc": 0.63, "mean_coverage": 0.91,
                     "warnings": ["object_detection_disabled: note-taking/phone confidence capped"]}},
 "listeners": [{
   "participant_track_id": "D", "coverage": 0.88,
   "oei": {"value": 58.2, "confidence": 0.71, "components": {"A":0.52,"K":0.05,"N":0.22,"D":0.06},
           "label_type": "observation", "note": "Composite of visible behaviour; not a measure of attention or interest."},
   "states": {"speaker_oriented": {"ratio": 0.51, "label_type": "inference", "confidence_mean": 0.74},
              "looking_down": {"ratio": 0.33, "label_type": "observation"},
              "possible_note_taking": {"ratio": 0.22, "label_type": "inference", "confidence_mean": 0.62,
                                       "caps": ["no_object_detection"]},
              "possible_distraction": {"count": 1, "total_s": 14.2, "label_type": "inference", "confidence": 0.51}},
   "acknowledgment": {"nod_rate_per_min": 1.8, "n": 9, "timing": {"at_pause": 4, "at_turn_end": 3, "mid_speech": 2}},
   "turn_prep_profile": {"turns": 7, "lean_forward_pct": 0.57, "oriented_before_turn_pct": 0.86, "median_lead_s": 1.4}
 }],
 "matrix": {"listeners": ["B","C","D"], "speakers": ["A","B","C","D"],
            "speaker_oriented_ratio": [[0.81,null,0.55,0.47],[0.62,0.70,null,0.58],[0.45,0.51,0.49,null]]}
}
```

---

## 15. Frontend Visualization Requirements

Route: `MeetingAnalysis → Listeners` tab, using `useListenerAnalysis(meetingId)` + `useJobPolling`; Recharts + custom SVG (no new heavy dependencies).

| Component | Spec |
|---|---|
| `ListenerQualityBanner` | scene mode, fps, `signals_available` chips (Hands ✓ / Objects ✗), coverage, warnings such as "Note-taking labels capped (object detection off)". |
| `AttentionTimeline` (swimlane) | top band: speaker turns coloured by speaker; below, **one lane per listener** with state runs (colour = state; opacity = confidence; hatched = `not_observable`, never coloured as "away"). Event glyphs: nod ▲, side-exchange ↔, possible-distraction ⚑. Click → seek video and open segment inspector. Brush-zoom shared with doc 13 timeline. |
| `SegmentInspector` | for the selected speaker turn: table of listeners (ratios, coverage, primary-state stacked bar, nod list with timing class, OEI + confidence) exactly like §10.2 example; "Why?" popover lists evidence terms and caps. |
| `WhoAttendsWhomMatrix` | heatmap `listener × speaker` of `speaker_oriented_ratio`; cell shows `%` and `observable_s`; cells with `coverage < 0.4` greyed. |
| `AudienceSummary` per speaker | dot-plot of listeners' orientation ratios (no averaging to a single "speaker score"). |
| `AttentionSeries` | stacked area of share of observable listeners by state (30 s buckets) with shared-focus windows shaded and decisions/proposals as markers. |
| `NodRaster` | per listener rows, ticks at nod times, aligned to speaker pauses/turn-ends (secondary strip showing speaker pauses). Histogram of nod timing classes. |
| `NoteTakingEvidence` | drill-down for a `possible_note_taking` run: mini-plots of head pitch_rel, hand motion energy, dominant frequency, object bbox presence; the **evidence checklist** (✓ head-down ✓ localised hand motion ✗ object detected). |
| `OEIPanel` | per-listener distribution (violin/strip across turns) + component breakdown; default sort **not** by score; disclaimer text; hidden when coverage < 0.4. |
| `TurnPrepProfile` | per listener: bars of cue frequencies before their own turns (oriented, lean-forward, hand-raise, head-up recovery). |
| `LlmInterpretationCard` | group-level narrative with evidence chips. |
| `OverlayToggle` (video player) | request annotated video with listener overlay (state label + confidence, direction arrows). |

UX rules: label chips **OBS / INF / INT**; text uses only the allowed vocabulary; colours for states are neutral categorical (no red/green "good/bad"); every percentage shows coverage; empty/unknown ≠ zero; a "How to read this" drawer states the facing ≠ listening principle, camera-angle and cultural caveats.

---

## 16. Validation, Calibration and Test Cases

### 16.1 Unit tests (synthetic signals)
| Test | Setup | Expectation |
|---|---|---|
| Geometry | two tracks at known image positions, listener heading synthesised toward speaker | `head_err < 3°`, `speaker_oriented` ≥ 0.95; rotate 60° away → 0 |
| Yaw sign self-calibration | flip sign in synthetic data | detector picks correct sign; ambiguous data → `yaw_sign_uncertain=true` |
| Baseline | add constant −12° pitch bias to a track | `pitch_rel` unchanged; not flagged `looking_down` |
| Head-down alone | pitch −25° for 10 s, hands absent/still | `looking_down` present, **no** `possible_note_taking` |
| Head-down + writing motion | pitch −22°, single-hand 3 Hz localised motion, 8 s | `possible_note_taking` conf ≥ 0.6 (≤ 0.7 cap without objects) |
| Head-down + no hand observability | hands missing | `looking_down` only, reason `hands_not_observable` |
| Large gesture | head-down + big arm sweeps | note-taking suppressed (×0.3) |
| Typing vs writing | both hands synchronised 4 Hz + laptop bbox | `possible_screen_use`, not note-taking |
| Nod | 2 cycles of 6° at 1.5 Hz on pitch | 1 episode, conf ≥ 0.6; 1.5° jitter noise → none; 8° single slow drop (looking down) → none; yaw oscillation → none (head shake) |
| Low fps | 4 fps | `nod_detectable=false`, nods `null` not 0 |
| Visibility | face lost 3 s | state `not_observable`, ratios over observable frames only, coverage reduced |
| Shared focus | 3 of 4 listeners aligned at 40° from speaker | they get `oriented_to_shared_focus`, not `looking_away` |
| Distraction | 6 s `looking_away` outside focus windows | `possible_distraction` (conf ≥ 0.5); 3 s → none; same during note-taking → none |
| Gallery mode | `scene_mode=gallery_tiles` | speaker-directed metrics `null(reason)`, note/phone/nod still computed |

### 16.2 Alignment tests
* **Spec example:** fixture reproducing §10.2 (125 frames; B 97/120, C 73/118, D 54/121 & 38/121) ⇒ exact ratios 0.81/0.62/0.45/0.31 and coverage 0.96/0.94/0.97.
* Overlapping speech: another speaker active for 2 s of a 12.5 s turn ⇒ those frames excluded, `overlap_excluded_s = 2.0`, `coverage` computed on the remaining time.
* Listener is also speaking (self) ⇒ excluded frames, nods flagged `during_own_speech`.
* Listener joins mid-turn / leaves ⇒ omitted outside track lifespan; not counted as away.
* Backchannel-only "speaker" interval (< 1 s) ⇒ no `listener_segment_stats` row.
* Reaction lag: a nod at t=132.6 (0.1 s after turn end) is attributed to the just-ended turn and classed `at_turn_end`.
* `pre_margin`: listener turns toward speaker at 119.8 s ⇒ `orientation_latency_s` ≤ 0.

### 16.3 Property / regression
Ratios ∈ [0,1]; mutually exclusive `primary_state_dist` sums to 1 ± 1e-6; adding a `not_observable` frame changes coverage but not other ratios; re-running with the same config yields identical rows; permuting track order has no effect; single-participant meeting ⇒ no listener rows; two participants ⇒ geometry Tier-B fallback.

### 16.4 Empirical calibration with real data
1. **Annotation set:** label 3–5 meetings (~60 min total) with a small tool (or ELAN/CSV) for states: speaker-oriented, looking-down, writing, laptop, phone, nod, distracted. Use the annotated-video worker's listener overlay to review and correct predictions faster than labelling from scratch. Two annotators on 20 % for agreement (Cohen's κ; report, do not assume).
2. **Metrics:** per-state precision/recall at frame level and event-level (nod tolerance ±0.5 s), calibration curve of `confidence` vs. empirical precision (binned reliability); tune weights/thresholds and rescale confidences; adopt `emit_conf` thresholds giving precision ≥ 0.7 for `possible_*` labels (target, to be confirmed empirically).
3. **Pseudo-ground truth for readiness:** AUC of `readiness_peak` for next-speaker prediction (§8.7).
4. **Bias/fairness checks:** compare `observable` rate and detection confidence across glasses/no glasses, skin-tone bins and camera angles (if consented metadata exist) and report disparities; do not deploy state labels for groups with materially lower observability without a warning.
5. **Regression pack:** freeze 2–3 short clips with expected state runs (± tolerance) for CI.

### 16.5 Performance
Target: 1 h, 6 tracks, 10 Hz ⇒ 216 k frames/track; vectorised NumPy pipeline ≈ 30–90 s; memory ≈ `n_tracks × n_states × T × 4 B` ≈ 6 × 14 × 36 000 × 4 ≈ 12 MB per hour of grid — fine.

---

## 17. LLM Interpretation Layer

* **Input:** listener meeting stats, `matrix`, per-listener OEI components (with coverage/confidence), events (top 15), `turn_prep_profile`, run quality and `signals_available`, and doc 13's decisions/proposals list for context. No images, no frames.
* **System prompt essentials:** describe *visible behaviour patterns of the group*; use only the allowed vocabulary; never say a person "was listening/not listening/bored/engaged/uninterested"; every statement cites evidence keys and states *observation* vs *inference*; mention coverage/caps; highlight limitations (camera angle, glasses, cultural norms, neurodiversity, remote vs in-room); do not rank people; do not evaluate the speaker or the listeners.
* **Output schema:**
```json
{"group_patterns":[{"statement":"...", "evidence":["matrix.B->A","attention_series"], "type":"observation|inference"}],
 "notable_moments":[{"t_start":120.0,"t_end":132.5,"statement":"...","evidence":[...]}],
 "listener_notes":[{"participant_track_id":"D","statements":[{"statement":"...","evidence":[...],"type":"inference","confidence":0.6}],"limitations":["object detection off"]}],
 "data_quality_notes":["..."]}
```
* **Validator (mandatory):** JSON schema; evidence keys exist; blocklist regex (`\b(is|was|were) (listening|paying attention|bored|engaged|interested|uninterested|distracted)\b`, `disengaged|unfocused|rude|checked out|lazy|ignoring`) → reject/retry once, then fall back to a deterministic template summary; drop claims with `confidence < 0.4`. Cache by `prompt_hash` in `nts_listener_reports` (UPSERT), reuse the Phase 10 Groq client.

---

## 18. Limitations and Ethics

* Facing direction is a weak proxy for attention; people look away to think, listen with eyes closed, look at notes to *listen better*, or have gaze norms that differ by culture, disability or neurotype. Labels describe visible orientation only.
* Webcam/camera geometry, low resolution, glasses, masks, hair, lighting and occlusion degrade face pose; `human` models have known accuracy variation across demographics — hence coverage-gating, confidence caps, and the bias check in §16.4.
* Hand/phone/laptop evidence is inherently ambiguous without object detection; note-taking and phone labels stay explicitly "possible".
* In `gallery_tiles` recordings, orientation is toward one's own screen; speaker-directed metrics are unavailable by design.
* The platform must not be used to make employment, disciplinary or grading decisions about individuals from these outputs; recommended use is aggregate, retrospective meeting-dynamics analysis with participant consent, visible confidence, and retention limits per platform policy.

---

## 19. Implementation Roadmap (vertical slices)

1. **Slice A – Plumbing:** grid resampling, visibility/coverage, `listener_analysis_runs`, `listener_calibration` (baselines only), alignment engine (§10) with a **single** state (`looking_down` + `not_observable`) → `listener_segment_stats`, `/summary`, `SegmentInspector`, timeline lane. Reproduce the §10.2 example on fixtures.
2. **Slice B – Orientation:** geometry, yaw self-calibration, speaker-oriented / other-person / looking-away, shared focus, matrix + `WhoAttendsWhomMatrix`, gallery-mode fallback.
3. **Slice C – Nods & acknowledgment:** nod detector, timing classes tied to doc 13 pauses/acts, `NodRaster`, acknowledgment events.
4. **Slice D – Hands & activities:** motion features, note-taking scorer (no objects, cap 0.7), screen/phone heuristics, distraction, `NoteTakingEvidence` drill-down.
5. **Slice E – Composite & readiness:** OEI, engagement runs, readiness + turn-prep profiles, AUC validation.
6. **Slice F – `[CV+]` options:** object detection flag in `human_cv_script.js`, gesture/mesh persistence, cap relaxation, listener overlay in `video_annotation_worker`.
7. **Slice G – LLM + calibration:** LLM payload/validator/report, annotation set, reliability curves, threshold tuning, CI regression clips.
