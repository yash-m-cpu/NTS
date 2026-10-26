# 12 — Audio-Visual Speaker Attribution: Technical Design

| Field | Value |
|---|---|
| Companion | `11_SPEECH_DIARIZATION_PRD.md` (requirements, edge cases, acceptance criteria) |
| Algorithm version | `attr-1.0.0-baseline` |
| Scope | Given video + audio + existing visual tracks, output which `participant_track_id` is speaking in every speech segment, with calibrated confidence |
| MVP constraints | CPU only, Python 3.12, numpy/scipy/onnxruntime, no torch, no external model downloads at runtime |

Items marked **[VERIFY]** depend on repo facts not visible when this was written.

---

## 1. Design Summary

**Key idea:** audio tells us *when* speech happens; vision tells us *who could be producing it*; **temporal synchrony** between the two, plus continuity over time, tells us *who is*. Lip activity by itself is a weak, ambiguous cue, so it is used only (a) as a gate/veto and (b) as the signal correlated against the audio envelope.

**Method:** a speech-conditioned HMM over states `{track_1..track_N, UNKNOWN}` on a 100 ms grid.
- *Emissions:* per-slice log-linear evidence fusion with reliability weighting (§8).
- *Transitions:* hysteresis via pause-dependent switch probabilities (§11).
- *Decoding:* forward–backward posteriors (confidence) + Viterbi (path), aggregated into units (§9–10, 12).
- *Unknown handling:* first-class states, never forced assignment (§10).

**Why not the literal additive formula** (`audio + lip + sync + continuity + visibility + diar`): (1) audio speech probability is identical for every candidate, so it cannot discriminate between them; it is a gate and reliability input; (2) face visibility does not make someone more likely to speak, it makes the *other evidence about them* more trustworthy → multiplicative reliability; (3) continuity is a prior over time, not a per-slice score → HMM transitions; (4) unbounded sums of correlated terms overcount evidence → bounded evidence values in [−1, 1], reliabilities in [0, 1], softmax normalisation, tempered emissions.

---

## 2. Pipeline Overview

```
                 ┌──────────── existing ────────────┐
 video ──────────┤ cv_extraction (Human)            ├─► participant_tracks, feature_extractions (+mouth landmarks, pts_time)
                 └──────────────────────────────────┘
 audio ──► ffmpeg 16k mono ─► VAD prob ─┐
                          └► energy env ├─► [A] AudioFeatures
 faster-whisper (word ts) ──────────────┘         │
                                                  ▼
 [V] MouthFeatureSeries per track ──► [Q] quality/reliability ──► [S] Sync features (windowed xcorr, onset/offset)
                                                                     │
 optional diarization/embeddings ──► [D] label↔track mapping ────────┤
                                                                     ▼
                   [E] Emission scoring ─► [H] HMM (Viterbi + forward-backward) ─► [U] Unit assembly
                                                                     │
                       [C] calibration ◄─────────────────────────────┘
                                                                     ▼
                     attributed_segments + debug artifact ─► speech_analysis ─► listener_analysis
```

---

## 3. Required Features

### 3.1 Audio (all class O unless noted)
| Feature | Symbol | Source | Rate | Used for |
|---|---|---|---|---|
| VAD speech probability | `p_vad(t)` | Silero ONNX (reuse faster-whisper's bundled model if API allows **[VERIFY]**) / webrtcvad fallback | 32 ms | speech gating, slice audio weight |
| Speech mask + regions | `SpeechRegion[]` | thresholded/smoothed `p_vad` | — | unit boundaries |
| Band-limited log-energy envelope | `env(t)` | 100–4000 Hz, 25 ms window | 25 ms → resampled | sync correlation |
| Onset/offset times | `t_on, t_off` | region boundaries | — | onset/offset alignment |
| Whisper words | `Word(text, start, end, prob)` | faster-whisper `word_timestamps=True` | — | text allocation, short-utterance handling |
| Audio quality | SNR, noise floor, clipping | percentile-based | meeting-level + 10 s windows | reliability, unknown prior |
| Diarization labels (opt.) | `DiarSeg(label, start, end, overlap_flag)` | adapter | — | consistency evidence (§8.5) |
| Speaker embeddings (opt.) | `emb(seg)` | adapter | per unit | voice-profile propagation (§17) |
| Overlap flag (opt.) | | diarization/OSD | | overlap detection |

### 3.2 Visual (per track per frame)
| Feature | Symbol | Class | Source |
|---|---|---|---|
| Frame time | `t_pts` | O | video pts |
| Face bbox, detector confidence | `bbox, c_face` | O | existing Human output |
| Face-mesh validity/landmark confidence | `c_lm` | O | Human mesh (`face.mesh`), `face.faceScore/boxScore` |
| Head yaw/pitch/roll | `yaw, pitch, roll` | O | existing |
| Mouth landmarks (§4.2) | `L_mouth` | O | new persistence |
| Mouth aspect ratio | `MAR` | O→derived | §4.2 |
| Mouth opening ratio | `MOR` | derived | §4.2 |
| Mouth width, lip area | `MW, LA` | derived | §4.2 |
| MAR velocity | `dMAR` | derived | §4.2 |
| Mouth activity score | `a(t)` | derived | §5.3 |
| Occlusion flag | `occ_mouth` | derived | hand keypoints/landmark anomalies |
| Landmark jitter | `jit` | derived | frame-to-frame residual after motion compensation |
| Visibility (in-frame fraction of bbox) | `vis` | derived | bbox ∩ frame |
| Track lifetime | `[t_start,t_end]` | O | `participant_tracks` |

### 3.3 Temporal (per unit × candidate)
Speech onset/offset, mouth-movement onset/offset, sync lag (`argmax` cross-correlation), correlation peak and z-score vs far-lag baseline, track continuity (previous state posterior), pause context.

---

## 4. Feature Extraction

### 4.1 Audio
```python
def prepare_audio(media_path) -> AudioBundle:
    # 1. ffmpeg -vn -ac 1 -ar 16000 -f f32le  (stream to numpy; do NOT write temp WAV if STT already produced one [VERIFY])
    # 2. record audio_start_offset_s = audio stream start_time - video stream start_time (ffprobe)
    # 3. p_vad = silero_vad(wave, window=512 @16k -> 32 ms hop)
    # 4. speech_mask = hysteresis_threshold(p_vad, on=0.55, off=0.35); min_speech=0.10s; min_silence=0.15s; pad=0.05s
    # 5. env_raw = log(RMS(bandpass(wave,100,4000), win=25ms, hop=10ms) + 1e-6)
    # 6. env_norm = clip((env_raw - P5) / (P95 - P5 + eps), 0, 1)      # per-meeting percentiles
    # 7. quality: noise_floor = P10(env_raw over non-speech), SNR = P90(env over speech) - noise_floor (dB-ish), clipping_ratio
```
All audio timestamps are converted to the **master clock** (§6.1) immediately after extraction.

### 4.2 Mouth landmarks and metrics
Human (`@vladmandic/human`) returns a 468-point (478 with iris) MediaPipe-style face mesh in `face.mesh` (pixel coordinates, z relative) when `face.mesh.enabled` is true **[VERIFY config and current persistence]**. Mesh indices used (MediaPipe FaceMesh topology):

| Purpose | Indices |
|---|---|
| Inner-lip polygon (20 pts, ordered) | 78,191,80,81,82,13,312,311,310,415,308,324,318,402,317,14,87,178,88,95 |
| Inner upper/lower mid | 13 (upper), 14 (lower) |
| Inner mouth corners | 78 (left), 308 (right) |
| Outer corners | 61, 291 |
| Outer upper/lower mid | 0, 17 |
| Additional vertical pairs (robustness) | (82,87), (81,178), (312,317), (311,402) |
| Eye scale reference (outer eye corners) | 33 (right eye outer), 263 (left eye outer) |
| Nose bridge/tip for pose-normalisation | 168, 1 |

**Persistence (CV script change).** Per face per frame, emit a compact record instead of the full mesh:
```json
{"t": 12.4667, "track": "<track key>", "lm_conf": 0.93,
 "mouth": {"poly": [[x,y],...20], "outer": [[x,y]x6], "eye": [[x,y],[x,y]], "nose": [[x,y],[x,y]]}}
```
Coordinates are stored in **face-normalised space** (see below), 16-bit quantised, ≈ 100 bytes/face-frame. If the current script already stores the mesh, compute from it and skip the CV change. If neither is available for an existing meeting, backfill is a **re-run of CV extraction** (Human inference required; the "zero re-inference" property applies only to meetings processed after this change).

**Face-normalised space.** Rotate by the eye-line angle (removes roll), scale by inter-ocular distance `IOD = |p33 − p263|`, origin at midpoint of the eyes. Optional yaw compensation: divide horizontal mouth extent by `cos(yaw_clamped)` when |yaw| ≤ 45°; beyond that, MW/MAR-horizontal reliability decays (§5.2).

**Metrics (per frame):**
```
h_c   = mean over pairs of |y_upper - y_lower|             # inner vertical opening (normalised by IOD)
w_in  = |x_78 - x_308|                                       # inner horizontal width
MAR   = h_c / max(w_in, eps)                                 # mouth aspect ratio (inner)
MOR   = h_c / IOD                                            # opening relative to face size
MW    = |x_61 - x_291| / IOD                                 # outer width (smile/rounding cue)
LA    = polygon_area(inner_poly) / IOD^2                     # lip aperture area
dMAR  = central difference over ±1 frame, in MAR-units/second
```
Smoothing: 3-tap Savitzky–Golay (window 5 frames if fps ≥ 20, else 3) on MAR/MOR/LA **only**; `dMAR` computed from smoothed MAR.

### 4.3 Reliability terms (per track per frame; each in [0,1])
```
r_det   = clip((c_face - 0.4) / 0.4, 0, 1)
r_lm    = clip((c_lm  - 0.5) / 0.4, 0, 1)   # 0 if mesh invalid
r_size  = clip((IOD_px - 12) / 28, 0, 1)    # IOD below ~12 px: mouth too small; ≥40 px full
r_pose  = pose_reliability(yaw,pitch) = exp(-0.5*((|yaw|-0)/50)^4) * exp(-0.5*((|pitch|-0)/40)^4)
r_jit   = clip(1 - jit/jit_max, 0, 1)
r_occ   = 0 if occ_mouth else 1                  # smooth with 0.1 s hold
r_vis   = clip(visible_bbox_fraction, 0, 1)
q_vis   = (r_det * r_lm * r_size * r_pose * r_jit * r_occ * r_vis) ** (1/4)   # geometric-mean-like, stays gentle
```
`q_vis` gates lip evidence; `r_pose` also degrades `q_vis`, so extreme yaw loses lip weight but the track can remain a candidate (e.g., to keep continuity).

### 4.4 Occlusion detection
`occ_mouth = 1` if any of: (a) hand keypoint (Human hands/pose wrist) within the mouth ROI (inner-poly bbox expanded ×1.6) for ≥ 3 frames; (b) `c_lm` drops > 0.3 below its 1-s moving median while `c_face` stays high; (c) landmark polygon self-intersection/area anomaly (area < 0 or MAR > 3.0). Requires pose/hand data **[VERIFY availability per frame]**.

---

## 5. Feature Normalisation

### 5.1 Principle
Every evidence value fed to the emission is bounded: `e ∈ [−1, 1]`; every reliability `r ∈ [0,1]`. Raw signal scales are removed by *per-track robust baselines*, not global constants.

### 5.2 Per-track baselines (computed once per meeting, independent of attribution)
Let `G_sil` = frames where global VAD mask is off for ≥ 0.5 s (nobody speaks); `G_sp` = frames inside global speech regions.
```
noise_k    = median(|dMAR_k| over G_sil ∩ valid)           # closed/rest mouth jitter floor
scale_k    = P90(|dMAR_k| over G_sp ∩ valid)               # amplitude of speech-time motion
scale_k    = max(scale_k, median_j(scale_j) * 0.5, abs_floor)   # guards silent participants from noise amplification
mar_rest_k = P10(MAR_k over valid)                          # rest opening
mar_rng_k  = P90(MAR_k over G_sp ∩ valid) - mar_rest_k, floored similarly
```
`abs_floor` default 0.15 MAR-units/s (tunable). Baselines are recomputed with a per-track-lifetime window if a meeting exceeds 60 min or lighting/camera shifts (baseline drift), using 10-min blocks.

### 5.3 Mouth activity score
```
act_dyn(t)  = clip((|dMAR(t)| - noise_k) / (scale_k - noise_k + eps), 0, 1.5)
act_open(t) = clip((MAR(t) - mar_rest_k) / (mar_rng_k + eps), 0, 1.5)
a_inst(t)   = 0.65*act_dyn + 0.35*min(act_open,1)
a(t)        = causal-symmetric moving average of a_inst over 0.4 s (centered), clipped to [0,1]
```
Rationale: speech has *rapid* aperture changes (dMAR), while smiles/yawns/held-open mouths have openness without dynamics; the mix rewards movement, mildly penalises static openness.

### 5.4 Audio normalisation
`env_norm` (per-meeting percentiles) is further **detrended and z-scored per sync window** (§7.2). `p_vad` used as-is in [0,1].

### 5.5 Evidence mapping
```
sigmoid(x) = 1/(1+exp(-x)),  bipolar(v) = 2*v - 1
```

---

## 6. Time-Window Alignment

### 6.1 Master clock
Seconds from **container/video start**, `float64`.
- Video: `t = pts_time` (never `frame_idx/fps`). Detect VFR via `std(Δpts)/median(Δpts) > 0.05`.
- Audio: `t = sample_idx/16000 + audio_start_offset_s`.
- Whisper timestamps are relative to the audio buffer passed in → add `audio_start_offset_s`. If STT ran on a segment-trimmed or VAD-filtered buffer (`vad_filter=True`) **[VERIFY]**, remap using faster-whisper's `restore_speech_timestamps` behaviour or run with `word_timestamps` on the full buffer.
- Global A/V offset `av_offset_s` (default 0, config) shifts audio: `t_audio_master = t_audio + av_offset_s`. Auto-estimation in §6.5.

### 6.2 Analysis grid
- **Atom grid Δ = 0.1 s** (`slice_hop_s`). Slice `s` covers `[sΔ, (s+1)Δ)`, centre `t_s`.
- Visual signals resampled to the grid by linear interpolation onto **frame-rate-aware uniform grid** `T_v = 1/fps_eff` (fps_eff = median of measured fps, clamped 8–30) before windowed correlation; slice features are means over slice.
- Audio `p_vad` and `env` are resampled to the same grid by mean-pooling (and to `T_v` for correlation).

### 6.3 Windows
| Window | Length | Purpose |
|---|---|---|
| Activity smoothing | 0.4 s | `a(t)` |
| Sync window `W_sync` | 1.6 s centred on slice (shrinks to ≥ 0.8 s at region edges) | windowed cross-correlation |
| Onset/offset window | ±0.5 s around region boundary | onset/offset alignment |
| Track grace | 1.0 s | candidate persists after face loss |
| Lag search | ±0.30 s | audio/mouth lag |
| Far-lag baseline | ±[1.0, 2.5] s | null distribution for correlation |

Windows **never cross** a camera cut or a track gap > 0.5 s (mask instead).

### 6.4 Low-FPS handling
`fps_eff ≥ 15`: full weights. `10 ≤ fps_eff < 15`: `w_sync *= 0.7`, `w_onset *= 0.5`. `fps_eff < 10`: `w_sync *= 0.35`, `w_onset = 0`, confidence cap 0.75, warning `low_fps`. Syllabic mouth motion (3–8 Hz) aliases below ~12 fps.

### 6.5 A/V offset estimation (optional pass, run when ≥ 20 clean onsets exist)
For all speech-region onsets with a single dominant visible candidate (only one track with `q_vis ≥ 0.6`, `a` crossing threshold within ±1 s), collect `lag_i = t_mouth_on − t_audio_on`. If `median(lag)` outside ±0.12 s and MAD < 0.15 s → set `av_offset_s = median(lag) − expected_lead` where `expected_lead = −0.03 s` (mouth typically leads audio slightly); re-run scoring; record `av_desync` warning. Else keep 0.

---

## 7. Sync Features

### 7.1 Windowed audio–mouth correlation (primary discriminator)
For slice `s`, candidate `k`, window `W` (1.6 s):
```
x(τ) = band-pass(env(t+τ), 0.5–8 Hz)  detrend, z-score over window          # audio amplitude modulation ~ syllabic
y1(τ) = band-pass(MAR_k(t),  0.5–8 Hz) z-score over window
y2(τ) = band-pass(|dMAR_k(t)| smoothed 0.15 s, 0.5–8 Hz) z-score
for lag in [-0.30 .. +0.30] step T_v:          # positive lag = mouth lags audio; negative = mouth leads
    ρ1(lag) = corr(x(τ), y1(τ+lag)),  ρ2(lag) = corr(x(τ), y2(τ+lag))
ρ*      = max_lag max(ρ1, ρ2)   ;  lag* = argmax
null: same statistic computed at lags in ±[1.0, 2.5] s  →  μ0, σ0   (needs window padding; if unavailable use σ0 = 0.25, μ0 = 0)
z_sync  = (ρ* - μ0) / (σ0 + 0.05)
```
The far-lag null makes the score robust to mouths that are *always* moving (chewing, constant talking) and to slowly varying signals; it asks "is the alignment better at the physiological lag than at implausible lags?".

Validity: audio window must contain speech (`mean p_vad ≥ 0.4`) and audio variance above floor; visual window must have ≥ 70 % valid frames after interpolation of gaps ≤ 0.2 s.

```
e_sync   = 2*sigmoid((z_sync - 1.5)/0.8) - 1                    # ~0 at z=1.5? shifted:  z<0 → ≈ -1 (anti-evidence weak), z≈1.5 → 0, z≥3.5 → ≈ +0.9
r_sync   = frac_speech_in_window(clip 0..1, cap at 0.6→1)  *  q_vis_mean * fps_factor
```
Note: an `e_sync` negative value is *soft* negative evidence (misalignment), scaled down by `r_sync`; hard vetoes come only from the closed-mouth rule (§8.2).

### 7.2 Lip activity evidence (gate + veto + weak positive)
```
e_lip = bipolar( clamp(a_mean_slice / a_ref, 0, 1) )       # a_ref = 0.5  → a ≥ 0.5 counts as fully active
r_lip = q_vis
closed_mouth_veto: if q_vis ≥ 0.6 and mean p_vad ≥ 0.6 over 0.4 s and a_mean < 0.08 and MAR ≤ mar_rest_k + 0.15*mar_rng_k
                   → e_lip = -1, r_lip = 1, veto=True
```
### 7.3 Onset/offset alignment
Computed **per unit boundary**, then broadcast to slices within ±0.5 s of the boundary.
```
mouth_on(k) = first t in [t_on-0.5, t_on+0.5] where a(t) crosses θ_on (0.35) with hysteresis θ_off=0.20, requires mouth was "quiet" (a<θ_off) for ≥ 0.15 s before
lag_on      = mouth_on - t_on          (expected μ_on ≈ -0.05 s, σ_on = 0.15 s)
e_on        = 2*exp(-0.5*((lag_on - μ_on)/σ_on)^2) - 1      # if mouth already active before window (no quiet lead) → not observable → r_on=0
              if no crossing in window → e_on = -0.6
r_on        = observable ? q_vis * min(1, silence_before / 0.3) : 0     # needs ≥0.3 s preceding silence to be informative
```
Analogous `e_off` at `t_off` with quiet-lag expected +0.10 s; final `e_onoff = mean of available e_on,e_off`.

### 7.4 Mouth activity during silence (track-level, for trust)
`silence_activity_k = mean(a_k over G_sil, valid)`. If > 0.35 the track's mouth moves without speech (chewing/gum/tic/constant expressions): set `trust_k = 0.6` and multiply `r_lip` by `trust_k`. `sync` is unaffected (already null-controlled).

---

## 8. Candidate Generation & Scoring

### 8.1 Candidates
For slice `s`:
- `viable(k)`: track alive at `t_s`, **or** alive within grace (1.0 s) → status `degraded`.
- Candidate set `C(s) = {k viable} ∪ {UNK}`. `UNK` represents both off-screen and ambiguous (typed after decoding, §10).
- If `|viable| = 0`: state is forced to `UNK` with reason `no_face_tracks`/`no_visual_match`.
- Duplicate tracks (IoU > 0.7 for ≥ 1 s) are grouped; group members share evidence and tie → `AMBIGUOUS` with `duplicate_track`.

### 8.2 Emission (log-score per candidate)
```
z_k(s) = w_lip  * r_lip_k  * e_lip_k
       + w_sync * r_sync_k * e_sync_k
       + w_on   * r_on_k   * e_onoff_k
       + w_diar * r_diar_k * e_diar_k                # 0 when no diarization
       + w_pose * r_pose_k * e_pose_k                # small, optional (§8.6)
       + b_k                                          # 0 by default (uniform prior)
z_UNK(s) = b_UNK
       + w_uv * (1 - max_k q_vis_k)                  # nobody reliably visible → favour UNK
       + w_ua * (1 - max_k max(0, e_sync_k*r_sync_k, e_lip_k*r_lip_k))   # nobody shows positive evidence
       + w_ubg * background_speech_indicator          # low-energy, stable, no sync
       - w_ud * max_k(r_diar_k * e_diar_k)+           # diarization strongly points to a visible track → lower UNK
if veto_k: z_k(s) -= veto_penalty (default 3.0)      # additive after the sum, keeps ranking explicit
```
Default weights (`AttributionConfig.weights`): 

| Weight | Value | Rationale |
|---|---|---|
| `w_lip` | 1.0 | gate/support |
| `w_sync` | 1.6 | main discriminator |
| `w_on` | 0.6 | strong when observable, often not |
| `w_diar` | 1.5 | when mapping confident |
| `w_pose` | 0.2 | weak |
| `b_UNK` | −0.5 | mild reluctance to abstain when evidence exists |
| `w_uv` | 2.0 | |
| `w_ua` | 1.0 | |
| `w_ubg` | 1.0 | |
| `w_ud` | 1.0 | |
| `veto_penalty` | 3.0 | |
| `temperature T` | 1.0 | recalibrated (§18.4) |

Slice emission probabilities (before temporal model):
```
p_k(s) = softmax_k(z_k(s) / T)      over C(s)
```
### 8.3 Non-speech slices
Slices with `p_vad_smoothed < 0.5` are **not decoded**; they are removed from the HMM chain and carry a `gap` attribute (time since previous speech slice), used by transitions (§11).

### 8.4 Evidence-independence rule (for HIGH tier)
`independent_support(k) = (mean_slice r_sync*e_sync > 0.25) OR (mean r_diar*e_diar > 0.25)`. Winner without independent support cannot be HIGH.

### 8.5 Diarization consistency evidence (when available)
Given mapping `M: label → track | NONE` with confidence `m_conf(label)`:
```
for slice s with active label ℓ (dominant in diar over slice):
    if M(ℓ) == k:            e_diar_k = +1
    elif M(ℓ) == NONE:       e_diar_k = -0.6 for all visible k; boosts UNK via w_ud term (inverted: UNK gets +)
    else (M(ℓ) == j ≠ k):    e_diar_k = -0.8
    r_diar = m_conf(ℓ) * diar_local_reliability   # diar_local_reliability = 1 - overlap_flag*0.5
```
**Mapping estimation** (`diar_mapping.py`), iterative:
```
1. Visual-only per-slice posteriors p_k(s) from §8.2 without diar terms.
2. Co-occurrence  C[ℓ,k] = Σ_s 1[ℓ active at s] * p_k(s) * audio_w(s);  C[ℓ,UNK] similar with p_UNK
3. Solve assignment via Hungarian on -log-normalised C with allowance for label→NONE when C[ℓ,UNK]/Σ_k C[ℓ,·] > 0.5
   (many labels may map to the same track if Σ within-track speech supports it: relax to "each label picks argmax if share ≥ 0.6")
4. m_conf(ℓ) = share of label ℓ mass on its chosen state, penalised by margin: m_conf = share - 0.5*second_share
5. Re-run emission with diar evidence; recompute C; repeat up to 3 iterations or until mapping unchanged.
```
Conflict logging: any ≥ 1.0 s run where diar-mapped track loses to a different track with `z` gap ≥ 1.5 → `diar_visual_conflict`.

### 8.6 Head-pose evidence (optional, off by default in MVP; enable via `w_pose>0`)
`e_pose` = small positive when head yaw/pitch micro-motion (RMS of Δ over 0.5 s) correlates with `env` (speakers often gesture/nod while speaking); weak and confounded by listeners nodding → default 0.

### 8.7 Turn-continuity component
Handled by transitions (§11), not per-slice scores, with one additional per-slice term for **track-boundary continuity**: when a track disappears (turned/occluded) < 1.0 s ago while confidently speaking (`γ_k > 0.7`), its `r_*` are zero but transition stay-probability keeps its state alive (grace).

---

## 9. Temporal Model (HMM)

State space `S = {k ∈ viable tracks over full meeting} ∪ {UNK}`. Per slice, non-viable tracks have emission `ε` (1e-4) rather than −∞ to permit recovery from tracker glitches.

### 9.1 Emission
`B_s(k) = p_k(s)^γ` with **emission power `γ = 0.30`** (default). Slices overlap heavily (1.6 s windows advanced by 0.1 s), so treating them as independent overcounts evidence ≈ 16×; `γ` compensates. Tuned on labelled data (§18.4).

### 9.2 Transitions (§11)

### 9.3 Decoding
```
α = forward(B, A);  β = backward(B, A);   γ_post(s,k) = normalise(α_s(k) β_s(k))   # posterior
π = viterbi(B, A)                                                                   # single best path
```
Complexity `O(|slices| · N²)`; N ≤ ~12 → trivial (1 h ≈ 36 k slices).

### 9.4 Segmentation of the chain
The chain is split at camera cuts (fresh initial distribution, uniform with UNK bias) and at gaps > 5 s (optional: reset to a broad prior; default: keep chain but with maximal switch probability).

---

## 10. Winner Selection, Unknown Handling, Confidence

### 10.1 Attribution units
Units are built from VAD regions split by (a) pauses ≥ 0.3 s (already region boundary), (b) diarization speaker changes, (c) > 8 s max length, (d) **Viterbi path changes** meeting the switch criteria of §12. Whisper words are assigned to units by word midpoint.

### 10.2 Per-unit decision
```
audio_w(s)  = p_vad_smoothed(s) * energy_weight(s)          # energy_weight = clip(env_norm/0.2, 0.3, 1.0): quiet frames count less
mass_x      = Σ_s audio_w(s) * γ_post(s,x) / Σ_s audio_w(s)        for x in S
winner      = argmax mass_x ;  runner_up = second ;  margin = mass_win - mass_run
conf_raw    = mass_win
coverage    = Σ_s audio_w(s) * max_k(q_vis_k(s)) / Σ_s audio_w(s)   # how much of the unit had any reliable visual evidence
conf_pre    = conf_raw * (0.6 + 0.4*coverage)
conf        = calibrate(conf_pre)                            # isotonic/Platt (§18.4); identity until calibrated
```
Caps (applied in order): unit < 0.4 s → 0.60; no sync evidence available → 0.65; `fps<10` → 0.75; no independent support → 0.85; diar conflict → 0.70; overlap → 0.70; `audio_quality=poor` → 0.70.

### 10.3 Types and tiers
```
if winner == UNK and mass_UNK >= 0.5:
      type = UNKNOWN_OFFSCREEN  if no viable candidate OR max_k(q_vis) < 0.35 OR (all visible mouths inactive AND max_k e_sync < 0)
      else UNKNOWN_AMBIGUOUS
elif conf < 0.35 or margin < 0.10 among visible candidates:
      type = UNKNOWN_AMBIGUOUS , candidate_hint = best visible track, hint_conf = conf
else:
      participant = winner
      tier = HIGH   if conf >= 0.80 and margin >= 0.30 and independent_support
             MEDIUM if conf >= 0.55
             LOW    if conf >= 0.35
```
`UNKNOWN_OFFSCREEN` is assigned only when the evidence *for* off-screen (no visible speaker matching) is present — not merely when visual evidence is weak; weak evidence → `UNKNOWN_AMBIGUOUS`. This distinction matters for speech analysis (an off-camera speaker vs. an unresolvable one).

### 10.4 Reason codes (multi-valued)
`no_face_tracks, no_visual_match, partial_face, mouth_occluded, landmarks_unreliable, low_fps, noisy_audio, background_speech, short_utterance, overlap_detected, possible_overlap, multi_mouth_activity, diar_visual_conflict, camera_cut, track_boundary, speaker_pose_degraded, av_desync, duplicate_track, track_fragmentation_suspected, possible_laughter, non_speech_vocalisation, asr_hallucination_suspected, conf_capped:<cap>, single_candidate_only`.

---

## 11. Speaker-Switch Detection, Hysteresis, Debouncing

### 11.1 Transition matrix (per slice)
Let `g` = gap (s) since previous *speech* slice; `Δ=0.1`.
```
p_sw(g) = p_cont + (p_pause - p_cont) * clip(g / 1.0, 0, 1)
          p_cont  = 0.004    # switch probability per slice while speech is continuous  (≈ 1 switch / 25 s continuous)
          p_pause = 0.30     # switch probability at the first speech slice after a ≥1 s pause
A[i,i] = 1 - p_sw(g)
A[i,j] = p_sw(g) * w_ij / Σ_j w_ij     (j ≠ i)   w_ij = 1 for visible tracks, w_iUNK = 1.5 (abstaining is cheaper than jumping)
at camera cut: p_sw = 0.5
```
This encodes: (1) speakers rarely change mid-utterance without a pause, (2) after a pause anyone may speak, (3) a switch mid-speech needs strong contradicting evidence (log-ratio ≈ ln(0.996/0.004·1/γ-adjusted)).

### 11.2 Minimum dwell / debounce (post-processing on the Viterbi/posterior path)
```
Given runs R = [(state, start, end, mean_post)] of consecutive same-state speech slices:
for run r with duration < min_dwell (0.40 s):
    if prev.state == next.state and r.state != prev.state and r.mean_post < 0.85:  merge r into neighbours     # A-B-A → A
    elif r.duration < 0.40 and r.mean_post < 0.60:  relabel r as UNKNOWN_AMBIGUOUS(hint=r.state) (do not steal from neighbours)
exceptions: run is a backchannel candidate (§13) and passes short-utterance rules; run coincides with a confident onset alignment
```
### 11.3 Switch acceptance criteria (splitting a unit / declaring a new turn)
A switch from `A` to `B` at time `t` inside a VAD region (no pause) is accepted only if **all**:
1. `B` holds the Viterbi state for ≥ 0.6 s (`min_switch_run`),
2. mean `γ_post(B) ≥ 0.70` over that run and mean `γ_post(A) ≤ 0.20`,
3. independent support for `B` (§8.4) over the run,
4. `A`'s lip activity is low (`a_A < 0.25`) or A occluded/absent after `t`.
Otherwise the region stays with `A`, flagged `possible_overlap` if `B` evidence is strong (speaker interjection).
Switch boundary is refined to the nearest of: VAD pause, `mouth_on(B)` minus expected lead, or the posterior crossing point.

---

## 12. Overlapping Speech

### 12.1 Detection (MVP, no diarization)
A slice is `possible_overlap` if **all**: `p_vad ≥ 0.6`; ≥ 2 visible candidates with `r_lip*e_lip ≥ 0.3` and `r_sync*e_sync ≥ 0.2` (both positive sync); and either `env` spectral spread (spectral flatness of 300–3400 Hz) above `overlap_flat_thresh` **or** the runner-up posterior ≥ 0.30 for ≥ 0.5 s. Overlap is **inferred, never observed**, in the baseline.

### 12.2 Output
Unit gets `secondary_track_ids` (0–2), `overlap: {source: "diarization"|"visual_heuristic", fraction}`; the primary is the higher-mass candidate; both confidences capped 0.70; text flagged `overlap_unreliable`; excluded from response-latency statistics; counted in `overlap_ratio` only when source=diarization, otherwise in a separate `possible_overlap_ratio`.

### 12.3 With diarization
Use diarization overlap segments directly (`overlap_flag`), and per-label activity to produce a set of simultaneously active tracks via the mapping (§8.5); primary/secondary by label mass.

---

## 13. Short Utterance & Backchannel Handling

| Duration | Rules |
|---|---|
| ≥ 0.8 s | Normal path |
| 0.4–0.8 s | Sync window shrinks to unit ± 0.3 s; `r_sync *= 0.7`; onset/offset evidence weights ×1.5 (short units are dominated by onset/offset); cap conf 0.80 |
| < 0.4 s | Conf cap 0.60, tier ≤ MEDIUM; require `a` peak within ±0.25 s and `e_lip > 0`; else `UNKNOWN_AMBIGUOUS` with hint |
| Any short unit **inside another speaker's active turn** (`prev.state == next.state ≠ candidate`) | Prior flip: candidates = *listeners*; require candidate lip activity peak *and* no veto; favour the listener with strongest onset alignment; default to `UNKNOWN_AMBIGUOUS(hint)` when the top two listeners are within margin 0.15. Do **not** absorb into the main speaker via debouncing if `e_onoff` for a listener ≥ 0.6. |

Backchannel flag: unit < 1.0 s, ≤ 3 Whisper words (or no confident words) inside another's turn.

---

## 14. Low-Confidence Handling

1. Keep every unit; never delete or silently reassign.
2. `LOW` and `UNKNOWN_*` are excluded from headline per-person metrics but included in `upper_bound` and `unattributed_share`.
3. **Second-pass refinement (optional, cheap):** build per-track *voice profiles* from HIGH units (§17 embeddings), or from lightweight prosodic descriptors in MVP (median F0, mean log-energy, spectral centroid; 3-dim; weak), then re-score LOW units with a voice-consistency term; if unavailable, skip.
4. **Review queue:** surface LOW/AMBIGUOUS units sorted by duration in the UI; corrections stored as overrides and exported as labelled data for calibration.
5. Confidence never inflated by post-processing; merges keep the *minimum* of participating conf values weighted by duration.

---

## 15. Confidence Calculation (summary)

`conf = calibrate( mass_win × (0.6 + 0.4·coverage) )`, then caps (§10.2). Interpretation: the posterior mass that the temporal model gives to the winner, discounted when little of the unit had reliable visual evidence. `calibrate` is a monotone map fitted with isotonic regression on `(conf_pre, correct)` from labelled units; reliability diagrams and ECE are produced by the harness (§18.4). Until fitted → identity and API flag `confidence_calibrated=false`.

---

## 16. Data Structures

### 16.1 Python (Pydantic v2 / dataclasses) — `app/services/attribution/types.py`
```python
from __future__ import annotations
from enum import StrEnum
from typing import Literal, Optional
from pydantic import BaseModel, Field
import numpy as np

class StateType(StrEnum):
    TRACK = "TRACK"
    UNKNOWN_OFFSCREEN = "UNKNOWN_OFFSCREEN"
    UNKNOWN_AMBIGUOUS = "UNKNOWN_AMBIGUOUS"

class Tier(StrEnum):
    HIGH = "HIGH"; MEDIUM = "MEDIUM"; LOW = "LOW"; UNKNOWN = "UNKNOWN"

class AudioBundle(BaseModel):
    sr: int = 16000
    audio_start_offset_s: float
    duration_s: float
    p_vad: np.ndarray            # shape [T_a], float32, hop 0.032 s (see vad_hop_s)
    vad_hop_s: float
    env_raw: np.ndarray          # log energy, hop env_hop_s
    env_norm: np.ndarray
    env_hop_s: float
    regions: list["SpeechRegion"]
    quality: "AudioQuality"
    model_config = {"arbitrary_types_allowed": True}

class AudioQuality(BaseModel):
    snr_db: float; noise_floor: float; clipping_ratio: float
    speech_ratio: float; label: Literal["good","degraded","poor"]

class SpeechRegion(BaseModel):
    region_id: int
    start: float; end: float          # master clock, seconds
    mean_p_vad: float; mean_energy: float

class Word(BaseModel):
    text: str; start: float; end: float; prob: float

class SttSegment(BaseModel):
    stt_id: int; start: float; end: float; text: str
    avg_logprob: float; no_speech_prob: float
    words: list[Word] = []

class DiarSeg(BaseModel):
    label: str; start: float; end: float; overlap: bool = False

class MouthFrame(BaseModel):            # one row of the series (stored columnar in npz; this is the logical schema)
    t: float
    track_id: str
    mar: float; mor: float; mw: float; la: float; dmar: float
    c_face: float; c_lm: float
    yaw: float; pitch: float; roll: float
    iod_px: float; jitter: float
    occ_mouth: bool; visible_frac: float
    q_vis: float

class MouthSeries(BaseModel):           # per track, uniform grid after resampling
    track_id: str
    t0: float; hop_s: float
    arrays: dict[str, np.ndarray]       # keys: mar, mor, mw, la, dmar, a, q_vis, valid(bool), yaw, pitch, occ_mouth
    baselines: "TrackBaseline"
    lifetime: tuple[float, float]
    model_config = {"arbitrary_types_allowed": True}

class TrackBaseline(BaseModel):
    noise: float; scale: float; mar_rest: float; mar_rng: float
    silence_activity: float; trust: float; valid_fraction: float

class SliceEvidence(BaseModel):         # per slice per candidate; persisted only in debug artifact
    s: int; t: float
    track_id: Optional[str]             # None for UNK
    e_lip: float; r_lip: float
    e_sync: float; r_sync: float; z_sync: float; lag: float
    e_onoff: float; r_on: float
    e_diar: float; r_diar: float
    e_pose: float; r_pose: float
    veto: bool
    z: float; p: float                  # emission logit and softmax prob
    post: float                         # HMM posterior

class AttributedUnit(BaseModel):
    unit_id: int
    start: float; end: float
    region_id: int
    stt_ids: list[int]
    text: Optional[str]; words: list[Word] = []
    state_type: StateType
    participant_track_id: Optional[str]
    confidence: float                   # calibrated
    confidence_raw: float
    confidence_calibrated: bool
    tier: Tier
    margin: float
    runner_up_track_id: Optional[str]
    candidate_hint_track_id: Optional[str]
    secondary_track_ids: list[str] = []
    overlap: Optional[dict] = None      # {"source": "diarization|visual_heuristic", "fraction": float}
    coverage: float
    reason_codes: list[str]
    evidence_summary: dict[str, float]  # mean r*e per component for winner and runner-up
    diar_label: Optional[str] = None
    evidence_class: Literal["I"] = "I"

class AttributionConfig(BaseModel):
    slice_hop_s: float = 0.1
    sync_window_s: float = 1.6
    lag_max_s: float = 0.30
    weights: dict[str, float] = {"lip":1.0,"sync":1.6,"on":0.6,"diar":1.5,"pose":0.0,
                                 "uv":2.0,"ua":1.0,"ubg":1.0,"ud":1.0}
    b_unk: float = -0.5
    veto_penalty: float = 3.0
    temperature: float = 1.0
    emission_power: float = 0.30
    p_cont: float = 0.004
    p_pause: float = 0.30
    min_dwell_s: float = 0.40
    min_switch_run_s: float = 0.60
    grace_s: float = 1.0
    tier_high: float = 0.80; tier_medium: float = 0.55; tier_low: float = 0.35
    margin_high: float = 0.30; margin_min: float = 0.10
    short_unit_s: float = 0.40
    max_unit_s: float = 8.0
    pause_split_s: float = 0.30
    a_ref: float = 0.5
    abs_floor_dmar: float = 0.15
    av_offset_s: float = 0.0
    use_diarization: bool = False
    seed: int = 1234
```
### 16.2 Database (Alembic, additive) — types are PostgreSQL; FKs follow existing naming **[VERIFY table/PK names]**
```sql
CREATE TABLE attribution_runs (
  id UUID PRIMARY KEY, meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  algorithm_version TEXT NOT NULL, config JSONB NOT NULL, config_hash TEXT NOT NULL,
  status TEXT NOT NULL,                              -- ok | completed_with_warnings | no_audio | failed
  warnings JSONB NOT NULL DEFAULT '[]',
  stats JSONB NOT NULL DEFAULT '{}',                 -- coverage, unknown rates, fps_eff, audio_quality, timings
  confidence_calibrated BOOLEAN NOT NULL DEFAULT FALSE,
  is_current BOOLEAN NOT NULL DEFAULT FALSE,
  debug_object_key TEXT, created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (meeting_id, config_hash, algorithm_version)
);
CREATE UNIQUE INDEX ux_attribution_current ON attribution_runs(meeting_id) WHERE is_current;

CREATE TABLE attributed_segments (
  id BIGSERIAL PRIMARY KEY, run_id UUID NOT NULL REFERENCES attribution_runs(id) ON DELETE CASCADE,
  meeting_id UUID NOT NULL, unit_index INT NOT NULL,
  start_s DOUBLE PRECISION NOT NULL, end_s DOUBLE PRECISION NOT NULL,
  state_type TEXT NOT NULL, participant_track_id UUID REFERENCES participant_tracks(id),
  candidate_hint_track_id UUID, runner_up_track_id UUID, secondary_track_ids UUID[] DEFAULT '{}',
  confidence REAL NOT NULL, confidence_raw REAL NOT NULL, tier TEXT NOT NULL, margin REAL,
  coverage REAL, reason_codes TEXT[] NOT NULL DEFAULT '{}', overlap JSONB,
  text TEXT, words JSONB, stt_ids INT[], diar_label TEXT,
  evidence_summary JSONB, override_track_id UUID, override_by UUID, override_at TIMESTAMPTZ,
  evidence_class CHAR(1) NOT NULL DEFAULT 'I',
  UNIQUE (run_id, unit_index)
);
CREATE INDEX ix_attr_seg_meeting_time ON attributed_segments(meeting_id, start_s);
CREATE INDEX ix_attr_seg_track ON attributed_segments(participant_track_id);

CREATE TABLE speaker_label_mappings (
  id BIGSERIAL PRIMARY KEY, run_id UUID NOT NULL REFERENCES attribution_runs(id) ON DELETE CASCADE,
  diar_label TEXT NOT NULL, participant_track_id UUID, mapping_type TEXT NOT NULL,  -- TRACK | NONE
  mapping_confidence REAL NOT NULL, mass JSONB
);

CREATE TABLE mouth_feature_series (
  id BIGSERIAL PRIMARY KEY, meeting_id UUID NOT NULL, participant_track_id UUID NOT NULL REFERENCES participant_tracks(id),
  object_key TEXT NOT NULL,                          -- MinIO .npz (columnar)
  fps_eff REAL, valid_fraction REAL, baseline JSONB, extractor_version TEXT NOT NULL,
  UNIQUE (meeting_id, participant_track_id, extractor_version)
);

CREATE TABLE speech_metrics (
  id BIGSERIAL PRIMARY KEY, run_id UUID NOT NULL, meeting_id UUID NOT NULL,
  participant_track_id UUID,                          -- NULL = conversation-level
  metric TEXT NOT NULL, value DOUBLE PRECISION, value_low DOUBLE PRECISION, value_high DOUBLE PRECISION,
  payload JSONB, status TEXT NOT NULL DEFAULT 'ok',   -- ok | insufficient_evidence | not_applicable
  evidence_class CHAR(1) NOT NULL, mean_confidence REAL, unattributed_share REAL,
  UNIQUE (run_id, participant_track_id, metric)
);
CREATE TABLE listener_metrics (LIKE speech_metrics INCLUDING ALL);
CREATE TABLE listener_events (
  id BIGSERIAL PRIMARY KEY, run_id UUID NOT NULL, meeting_id UUID NOT NULL,
  participant_track_id UUID NOT NULL, event_type TEXT NOT NULL,   -- nod|shake|hand_to_face|looking_down|face_absent
  start_s DOUBLE PRECISION NOT NULL, end_s DOUBLE PRECISION NOT NULL,
  confidence REAL, overlapped_speaker_track_id UUID, evidence_class CHAR(1) NOT NULL DEFAULT 'I'
);
```
Dense per-slice debug: `s3://<bucket>/<org>/<meeting>/attribution/<run_id>/debug.json.gz` (columnar arrays, ≤ 50 MB/h).

### 16.3 API payload (example)
```json
{
  "run_id": "…", "algorithm_version": "attr-1.0.0-baseline", "confidence_calibrated": false,
  "coverage": {"speech_s": 1834.2, "high": 0.61, "medium": 0.19, "low": 0.06, "unknown_ambiguous": 0.08, "unknown_offscreen": 0.06},
  "segments": [{
    "start": 12.40, "end": 15.90, "state_type": "TRACK", "participant_track_id": "trk_3",
    "confidence": 0.86, "tier": "HIGH", "margin": 0.61, "runner_up_track_id": "trk_1",
    "reason_codes": [], "evidence_class": "I",
    "text": "…", "evidence_summary": {"lip": 0.71, "sync": 0.58, "onoff": 0.44, "diar": null}
  }]
}
```

---

## 17. Pseudocode

### 17.1 Orchestrator
```python
def run_attribution(meeting_id, cfg: AttributionConfig) -> AttributionResult:
    audio   = load_audio_bundle(meeting_id)                      # §4.1 (cached from STT stage)
    stt     = load_stt_segments(meeting_id)                      # words with master-clock timestamps
    tracks  = load_tracks(meeting_id)
    series  = build_mouth_series(meeting_id, tracks, cfg)        # §4.2–4.4 + §5.2–5.3 -> dict[track_id, MouthSeries]
    warnings = precheck(audio, series, cfg)                      # §13 PRD (no_audio, low_fps, landmarks_missing ...)
    if warnings.fatal: return failed_result(warnings)

    cuts    = detect_camera_cuts(meeting_id, series)             # from CV shot signal or bbox-mass change
    diar    = maybe_run_diarization(audio, cfg)                  # optional adapter (§18); None in baseline
    grid    = make_grid(audio.duration_s, cfg.slice_hop_s)       # speech slices only
    sync    = compute_sync_features(grid, audio, series, cuts, cfg)          # §7 (vectorised)
    ev      = compute_evidence(grid, audio, series, sync, cuts, diar_map=None, cfg=cfg)
    post, path = decode_hmm(ev, grid, cuts, cfg)                 # §9
    if diar:
        for it in range(3):
            diar_map = estimate_label_mapping(post, diar, grid)  # §8.5
            ev   = compute_evidence(..., diar_map=diar_map, cfg=cfg)
            post_new, path = decode_hmm(ev, grid, cuts, cfg)
            if converged(post, post_new) and it>0: break
            post = post_new
    path = debounce_runs(path, post, ev, cfg)                    # §11.2
    units = build_units(audio.regions, stt, diar, path, post, ev, cfg)       # §10.1, §11.3
    units = decide_units(units, post, ev, series, audio, cfg)                # §10.2–10.4, §12, §13
    units = apply_calibration(units, load_calibration(cfg))                  # §15
    return AttributionResult(units=units, stats=summarise(units, series, audio, warnings), debug=ev.debug_arrays())
```
### 17.2 Sync features
```python
def compute_sync_features(grid, audio, series, cuts, cfg):
    fps_eff = median_fps(series)
    x_full  = resample(bandpass(audio.env_norm, 0.5, 8.0), fps_eff)              # aligned to master clock (+ av_offset)
    out = {}
    for k, ms in series.items():
        y1 = zscore_windowable(bandpass(fill_short_gaps(ms.arrays['mar'], 0.2), 0.5, 8.0))
        y2 = zscore_windowable(bandpass(smooth(abs(ms.arrays['dmar']), 0.15), 0.5, 8.0))
        valid = ms.arrays['valid']
        # sliding windowed normalised cross-correlation via FFT / cumulative sums over all lags at once:
        rho1 = sliding_xcorr(x_full, y1, win=cfg.sync_window_s, lags=lag_range(cfg.lag_max_s), null_lags=null_range(1.0, 2.5))
        rho2 = sliding_xcorr(x_full, y2, ...)
        rho_star = np.maximum(rho1.peak, rho2.peak)
        mu0, sd0 = np.maximum(rho1.null_mu, rho2.null_mu), np.maximum(rho1.null_sd, rho2.null_sd) # conservative
        z = (rho_star - mu0) / (np.where(np.isfinite(sd0), sd0, 0.25) + 0.05)
        speech_frac = sliding_mean(audio.p_vad_on_grid, cfg.sync_window_s)
        r_sync = np.clip(speech_frac / 0.6, 0, 1) * sliding_mean(ms.arrays['q_vis'], cfg.sync_window_s) \
                 * (valid_frac(valid, cfg.sync_window_s) >= 0.7) * fps_factor(fps_eff)
        r_sync = mask_windows_crossing(r_sync, cuts, track_gaps(ms))
        out[k] = SyncFeatures(z=z, rho=rho_star, lag=lag_at_peak, e=2*sigmoid((z-1.5)/0.8)-1, r=r_sync)
    return out
```
*Implementation note:* `sliding_xcorr` should use FFT-based or `numpy.lib.stride_tricks.sliding_window_view` with vectorised dot products; at 15 fps × 1.6 s ≈ 24 samples and 19 lags per slice it is trivially cheap (≈ 36 k slices × N tracks × 19 lags × 24 ≈ 16 M MACs per track).

### 17.3 Evidence & emission
```python
def compute_evidence(grid, audio, series, sync, cuts, diar_map, cfg):
    S = len(grid.slices);  K = list(series)
    Z = np.full((S, len(K)+1), -np.inf); P = np.zeros_like(Z)
    for s, sl in enumerate(grid.slices):
        viable = [k for k in K if is_viable(series[k], sl.t, cfg.grace_s)]      # alive or within grace
        best_vis = max([q_vis_at(series[k], sl.t) for k in viable], default=0.0)
        pos = []
        for k in viable:
            a  = mean_a(series[k], sl); q = q_vis_at(series[k], sl.t)
            e_lip = bipolar(min(a / cfg.a_ref, 1.0)); r_lip = q * series[k].baselines.trust
            veto = (q >= 0.6 and audio.p_vad_at(sl) >= 0.6 and a < 0.08 and mar_near_rest(series[k], sl))
            if veto: e_lip, r_lip = -1.0, 1.0
            e_sync, r_sync = sync[k].e[s], sync[k].r[s]
            e_on, r_on = onoff_evidence(k, sl, grid, series, audio, cfg)
            e_d, r_d   = diar_evidence(k, sl, diar_map, cfg) if diar_map else (0.0, 0.0)
            z = (cfg.weights['lip']*r_lip*e_lip + cfg.weights['sync']*r_sync*e_sync
                 + cfg.weights['on']*r_on*e_on + cfg.weights['diar']*r_d*e_d) + 0.0
            if veto: z -= cfg.veto_penalty
            Z[s, K.index(k)] = z
            pos.append(max(0.0, e_sync*r_sync, e_lip*r_lip))
        z_unk = (cfg.b_unk + cfg.weights['uv']*(1-best_vis)
                 + cfg.weights['ua']*(1 - max(pos, default=0.0))
                 + cfg.weights['ubg']*background_indicator(audio, sl)
                 - cfg.weights['ud']*max_diar_pull(viable, sl, diar_map))
        Z[s, -1] = z_unk
        P[s, :] = softmax_masked(Z[s, :] / cfg.temperature)
    return Evidence(Z=Z, P=P, tracks=K, ...)
```
### 17.4 HMM
```python
def decode_hmm(ev, grid, cuts, cfg):
    S, N = ev.P.shape
    logB = cfg.emission_power * np.log(np.maximum(ev.P, 1e-4))
    alpha = np.zeros((S, N)); beta = np.zeros((S, N))
    alpha[0] = log_prior(N) + logB[0]                            # uniform over viable, UNK weight 1.5
    for s in range(1, S):
        A = transition_matrix(N, gap=grid.gap[s], cut=grid.after_cut[s], cfg=cfg)
        alpha[s] = logB[s] + logsumexp(alpha[s-1][:, None] + np.log(A), axis=0)
    beta[-1] = 0
    for s in range(S-2, -1, -1):
        A = transition_matrix(N, gap=grid.gap[s+1], cut=grid.after_cut[s+1], cfg=cfg)
        beta[s] = logsumexp(np.log(A) + logB[s+1] + beta[s+1], axis=1)
    post = softmax(alpha + beta, axis=1)
    path = viterbi(logB, A_fn, ...)                              # same transitions, argmax variant
    return post, path
```
`transition_matrix` per §11.1. Cache matrices by rounded `(gap, cut)`.

### 17.5 Unit decision
```python
def decide_unit(u, post, ev, series, audio, cfg):
    sl = slices_in(u)
    w  = audio_weight(sl)
    mass = (w[:, None] * post[sl]).sum(0) / w.sum()
    order = np.argsort(-mass); win, run = order[0], order[1]
    margin = mass[win] - mass[run]
    cov = (w * best_qvis(sl)).sum() / w.sum()
    conf_pre = mass[win] * (0.6 + 0.4*cov)
    reasons = collect_reasons(u, ev, series, audio)
    indep = independent_support(win, sl, ev)
    typ, tier, part = classify(win, mass, margin, conf_pre, ev, cfg, u.duration)   # §10.3
    conf = apply_caps(calibrate(conf_pre), u, reasons, indep, cfg)
    return u.with_(participant_track_id=part, state_type=typ, tier=tier, confidence=conf, ...)
```
---

## 18. Baseline Implementation Plan (uses existing components; ships first)

### 18.1 Module layout
```
backend/app/services/attribution/
    config.py            # AttributionConfig
    types.py             # §16.1
    timeline.py          # master clock, pts handling, av offset, cuts
    audio_features.py    # ffmpeg stream, VAD, envelope, quality
    mouth_features.py    # landmarks -> MAR etc., reliability, baselines, series builder
    sync.py              # windowed xcorr, onset/offset
    evidence.py          # emission
    hmm.py               # forward-backward, viterbi, transitions
    units.py             # segmentation, debouncing, switch acceptance, short-utterance
    diar_mapping.py      # optional (Hungarian)
    calibration.py       # isotonic; load/save
    analysis/speech_metrics.py, analysis/listener_metrics.py
backend/app/workers/speaker_attribution_worker.py       # ARQ task: loads data, calls run_attribution, persists
backend/app/workers/speech_analysis_worker.py
backend/app/workers/listener_analysis_worker.py
backend/scripts/human_cv_script.js                       # add --emit-mouth flag + pts_time
backend/tests/attribution/...
backend/eval/                                            # evaluation harness (§19)
```
### 18.2 Dependencies (all CPU, small)
`numpy`, `scipy` (signal, optimize.linear_sum_assignment), `onnxruntime` (only if Silero VAD not reachable through faster-whisper), `scikit-learn` (isotonic; optional, can hand-roll PAV), `pyarrow`/`numpy.savez_compressed` for series. No torch. Verify wheels build on the current base image (the project previously needed `libgl1-mesa-glx` for OpenCV; none of these add system libs).

### 18.3 Baseline defaults
Weights per §8.2; `w_pose=0`; `use_diarization=False`; calibration identity. Ship with `confidence_calibrated=false` and provisional thresholds.

### 18.4 Calibration & tuning procedure
1. Label ≥ 10 meetings (§19.1).
2. Grid-search / coordinate-descent over `{w_sync, w_lip, w_on, emission_power, p_cont, p_pause, b_unk, T}` minimising segment-level log-loss with a penalty for FSA; keep the weight vector simple and human-readable.
3. Fit isotonic `calibrate()` on `conf_pre` vs correctness of attributed units (cross-validated by meeting, never by segment).
4. Report ECE, reliability diagram, per-tier accuracy; set tier thresholds from the calibrated curve so that HIGH ≈ ≥ 90 % precision, MEDIUM ≈ ≥ 75 %.
5. Freeze `attribution_version`; store calibration artifact in MinIO and reference in `attribution_runs`.

---

## 19. Optional Future Improvements (ordered by cost/benefit; none in MVP)

| # | Improvement | Adds | Cost / risk | Adopt when |
|---|---|---|---|---|
| 1 | **Learned combiner over existing features** (LightGBM/logistic regression on the §16 evidence vector per slice/candidate, replacing hand weights but keeping HMM) | Better weighting, learned interactions (pose × sync), calibration for free | Needs ≥ 10–20 labelled meetings; CPU only | Labelled data exists; segment accuracy plateaus |
| 2 | **pyannote.audio diarization/OSD** (adapter, `WITH_DIARIZATION=1`) | Voice-consistency across meeting, true overlap flags, better off-camera handling | torch dependency (~GBs), CPU 0.3–1× realtime, gated HF weights → must be **mirrored in MinIO/baked into image** (HF DNS previously failed) | Off-camera/UNKNOWN rate is high or gallery layouts dominate |
| 3 | **Speaker embeddings (ECAPA-TDNN via SpeechBrain / WeSpeaker ONNX)** + per-track voice profiles bootstrapped from HIGH units | Propagates confident labels to LOW units, cross-check for diar merge/split; pure-ONNX export avoids torch | Small models (~20–80 MB); weights hosting as above; risk of overfitting to few HIGH units | LOW-confidence share > 15 % after (1) |
| 4 | **Active speaker detection (TalkNet / Light-ASD / LoCoNet)** on face crops + audio | Strong AV evidence replacing hand-crafted sync; robust to expressions | GPU strongly preferred; needs cropped 25 fps face videos (re-decode); licenses to verify | Hard-tier accuracy targets unmet; GPU available |
| 5 | **SyncNet-style AV sync confidence** as an extra evidence term (`e_syncnet`) | Learned lip-audio sync offsets/confidence, complements xcorr | GPU/torch; face-crop pipeline | With (4) or if xcorr underperforms on low fps |
| 6 | **Audio-visual speech separation** (e.g., AV-HuBERT/AVSE-style) | Resolves overlapping speech text and attribution | Heavy, research-grade, GPU | Overlap-heavy use cases, business demand |
| 7 | **Face re-ID to merge fragmented tracks** using Human face descriptors | Fixes `track_fragmentation_suspected` | Privacy review; tracker change | Fragmentation > 5 % of tracks |
| 8 | **Shot-boundary detection / layout classifier** | Better cut handling and `scene_layout_type` | Small | Cuts common |

Adapter interfaces (stable now, implemented later):
```python
class DiarizationAdapter(Protocol):
    def diarize(self, wave: np.ndarray, sr: int) -> list[DiarSeg]: ...
class EmbeddingAdapter(Protocol):
    def embed(self, wave: np.ndarray, sr: int, spans: list[tuple[float,float]]) -> np.ndarray: ...   # [n, d], L2-normalised
class ActiveSpeakerAdapter(Protocol):
    def score(self, meeting_id: str, track_id: str, t0: float, t1: float) -> np.ndarray: ...       # per-frame speaking prob
```
ASD/SyncNet scores plug into `compute_evidence` as extra bounded evidence terms with their own weights and reliabilities. Schemas do not change.

---

## 20. Evaluation

### 20.1 Ground truth
- Annotate in ELAN/Audacity-style CSV → converted to RTTM: `(start, end, speaker_label)` where `speaker_label ∈ {participant identifier mapped to participant_track_id, OFFSCREEN, OVERLAP-set}`. Annotators watch and listen; label **who is speaking**, mark off-camera voices, mark overlaps. Two annotators on ≥ 20 % of material; report Cohen's κ / frame agreement. Inter-annotator agreement bounds achievable accuracy.
- Track↔identity mapping done once per meeting by annotator (known mapping → no optimal-assignment forgiveness in the primary metric).
- Strata tags per meeting: layout (room/gallery), fps, SNR, #people, lighting, glasses/beards/masks, noise, off-camera share.
- Dev / test split by **meeting**, ≥ 30 % held-out.

### 20.2 Metrics (per meeting, macro/micro-averaged, stratified)
Let `ref(t)` and `hyp(t)` be frame-level (10 ms) labels over reference speech time `T_ref`, with `hyp ∈ {track_i, UNK_OFF, UNK_AMB}`.

| Metric | Definition |
|---|---|
| **Frame-level speaker attribution accuracy (time-weighted)** | `Σ 1[hyp==ref] / T_ref`, UNKNOWN counts as wrong for on-camera ref speech; correct for `ref=OFFSCREEN ∧ hyp=UNK_OFF` |
| **Accuracy among attributed** | Same over frames where `hyp ∈ tracks` and tier ≥ MEDIUM |
| **Coverage** | fraction of `T_ref` with tier ≥ MEDIUM |
| **Segment-level accuracy** | For each hypothesis unit, correct iff duration-majority of `ref` within unit equals `hyp` (≥ 60 % overlap); reported for tier ≥ MEDIUM and for all |
| **Diarization Error Rate** | `(FA + MISS + CONFUSION) / T_ref` with 0.25 s collar; `FA`= hyp speech with no ref speech, `MISS`= ref speech with no hyp speech (none expected as VAD-independent; ref-vs-VAD errors reported separately), `CONFUSION` = wrong track. UNKNOWN on-camera speech counted as MISS-attribution ("speaker miss") in a variant `DER_strict`; and as non-error in `DER_lenient`. Computed with `pyannote.metrics` or `dscore` (dev-only dependency). |
| **Confusion rate + matrix** | `N×N` (+UNK rows/cols) time-weighted; report top confusions and whether they are adjacent-position pairs |
| **Unknown attribution rate (UAR)** | `T(hyp∈UNK) / T_hyp_speech`; split OFFSCREEN vs AMBIGUOUS; also *unknown precision*: fraction of UNK_OFF time truly off-camera |
| **False speaker activation (FSA)** | Time where a track is attributed while ref says that participant is not speaking, `/ T_hyp_speech` |
| **Missed speaker activation (MSA)** | Time where ref says on-camera participant speaks but hyp ≠ that track, `/ T_ref_oncam` (splits into misattributed vs unknown) |
| **Overlap detection P/R/F1** | On reference overlap intervals (needs labelled overlap) |
| **Spurious switch rate** | Hyp switches with no ref switch within ±0.5 s, per minute |
| **Missed switch rate**, **switch boundary error** | Reference switches without hyp switch within ±0.5 s; median/p90 abs time error of matched switches |
| **Calibration** | ECE (10 bins), reliability diagram, Brier score; per-tier accuracy |
| **Lip-only baseline delta** | Same metrics for the lip-only baseline (`w_sync=w_on=0`, no HMM) to prove multimodal gain (AC-Q11) |
| **Runtime** | Wall-clock ratio, peak RSS |

Targets: PRD §17.2.

### 20.3 Ablations (mandatory in harness)
lip-only; +sync; +onset/offset; +HMM; +diar; `emission_power` sweep; FPS downsample (30→15→10→6); noise injection (SNR 20/10/5 dB); landmark dropout 10/30 %; A/V offset ±0.3 s.

---

## 21. Test Cases & Expected Behaviour

### 21.1 Unit tests (pure functions)
| ID | Test | Expected |
|---|---|---|
| U-01 | MAR on synthetic landmarks: closed (h=0) vs open (h=0.5·w) | MAR ≈ 0 vs ≈ 0.5, invariant to scale (×3) and roll (±30°) |
| U-02 | Timeline: VFR pts vs constant fps | Sync computed on `pts_time`; no drift error > 1 frame |
| U-03 | Audio offset: Whisper timestamps with `audio_start_offset=0.5 s` | All units shifted by exactly 0.5 s on master clock |
| U-04 | Sync: audio envelope = 4 Hz sinusoid bursts; mouth MAR same bursts with lag 0.1 s | `lag* ≈ +0.1 s ± T_v`, `z_sync > 4` |
| U-05 | Sync null: mouth = random 4 Hz unrelated bursts | `z_sync < 1.5` in ≥ 95 % windows |
| U-06 | Constant mouth motion (chewing at 3 Hz, continuous) with speech bursts | `z_sync` low (far-lag control) |
| U-07 | Baseline: silent participant with jitter | `scale_k` floored; `a(t)` ≈ 0 during rest |
| U-08 | Veto: valid frontal candidate, mouth closed, strong speech | `veto=True`, emission `z_k` ≤ others − 3 |
| U-09 | HMM hysteresis: emission flips A/B every 0.3 s with weak margin during continuous speech | Path stays constant (0 switches) |
| U-10 | HMM switch: after 1.2 s pause, emission strongly favours B | Switch accepted at first slice after pause |
| U-11 | Debounce: A(3 s) B(0.25 s, post 0.5) A(3 s) | Merged to A |
| U-12 | Short utterance in another's turn: listener L has strong onset alignment | Attributed L (MEDIUM cap ≤ 0.60) not merged |
| U-13 | Confidence caps | Each cap applied and reason-coded |
| U-14 | Determinism | Same inputs → byte-identical serialized units |
| U-15 | Isotonic calibration monotone & bounded | ✓ |
| U-16 | Diarization mapping: 3 labels, 3 tracks with clean co-occurrence | Hungarian returns identity; `m_conf` > 0.9; unmatched label → NONE |
| U-17 | Metrics: speech metrics recomputed from segments | Equal to fixture expected JSON; bounds `low ≤ value ≤ high` |

### 21.2 Scenario tests (synthetic evidence generator; deterministic seeds)
The generator produces `AudioBundle` + `MouthSeries` for scripted scenarios (who speaks when, noise, occlusion, fps), bypassing video for speed. Also 3–4 short real fixture clips (≤ 20 s) for integration.

| ID | Scenario | Expected behaviour |
|---|---|---|
| S-01 | Two people alternate with 0.5–1.5 s pauses, frontal, 25 fps | 100 % of units correct, HIGH; ≤ 1 boundary error > 0.35 s |
| S-02 | Same, but non-speaker smiles/nods (mouth moves without sync) | Speaker correct; smiler not selected; FSA ≈ 0 |
| S-03 | Both move mouths constantly (multi_mouth_activity), only A synchronised | A wins MEDIUM/HIGH; flag `multi_mouth_activity` |
| S-04 | Speaker off-camera, two visible people quiet | `UNKNOWN_OFFSCREEN`, `no_visual_match` |
| S-05 | Speaker off-camera, one visible person chewing | `UNKNOWN_OFFSCREEN` (sync null) — not attributed to chewer |
| S-06 | Speaker A turns to 70° yaw mid-turn | Attribution retained by continuity, cap 0.85 → MEDIUM/HIGH per evidence; reason `speaker_pose_degraded` |
| S-07 | Speaker hand covers mouth for 2 s | `mouth_occluded`; conf drops; unit stays with A if continuity high; else AMBIGUOUS |
| S-08 | Partial face at frame edge | `partial_face`; reliability down; correct if sync strong |
| S-09 | A and B overlap 1.5 s (both mouths + audio) without diarization | Primary A, secondary B (or reverse), `possible_overlap`, conf ≤ 0.70, text flag |
| S-10 | Same with diarization overlap labels | `overlap_detected` (source=diarization) |
| S-11 | Backchannel "mm-hm" by listener L (0.35 s) during A's turn | L (MEDIUM, ≤ 0.6) or AMBIGUOUS(hint=L); A's turn not split unless criteria met |
| S-12 | Participant enters frame mid-meeting while speaking | Before entry: OFFSCREEN; after entry+grace: attributed; `track_boundary` |
| S-13 | Participant leaves; speech continues 0.8 s | Retained via grace; afterwards OFFSCREEN |
| S-14 | Silent participant visible whole meeting | 0 attributed; `silent_participant` metric with visibility proof |
| S-15 | Background TV speech, low energy, no sync | `UNKNOWN_OFFSCREEN`, `background_speech`; excluded from totals if configured |
| S-16 | Noise burst (SNR 5 dB) while A speaks | Lower conf, `noisy_audio`; no new spurious switch |
| S-17 | Camera cut A→B mid-speech | State reset; no sync window straddles cut; `camera_cut` |
| S-18 | No audio track | `no_audio` status; pipeline elsewhere unaffected |
| S-19 | No face tracks | All OFFSCREEN; speech-only metrics |
| S-20 | fps = 8 | `low_fps`; sync weights reduced; cap 0.75; still correct on clean data |
| S-21 | A/V offset +0.3 s injected | Offset auto-estimated (§6.5) or warning `av_desync`; accuracy drop < 10 pts |
| S-22 | Duplicate track on same face | `duplicate_track`; tie → AMBIGUOUS if forced apart |
| S-23 | Whisper text over silence (hallucination) | Unit dropped, `asr_hallucination_suspected` |
| S-24 | Laughter by A with B smiling | Non-speech tag if text empty; A attributed or AMBIGUOUS, B not |
| S-25 | Landmarks missing 30 % random frames | Graceful reduction; accuracy drop < 15 pts; no crash |
| S-26 | Legacy meeting without mouth landmarks | `failed: landmarks_missing` with backfill hint |
| S-27 | Long meeting (1 h, 8 tracks) | Runtime/memory within NFR-1 |
| S-28 | Mirror-tile/video-in-video (known limitation) | Documented failure; test asserts flagged limitation doc, not correctness |

### 21.3 Integration / regression
- Job cascade: enqueue CV and STT in either order → attribution starts exactly once after both succeed; duplicate enqueue is idempotent.
- Re-run with same config → `is_current` swap atomic; API never returns partial run.
- Annotation worker reads attribution and renders overlay without calling Human/whisper.
- Golden-file regression: fixture clips' attributed JSON compared with tolerance (start/end ±20 ms, conf ±0.02).
- Guardrail test: LLM prompt template lacks forbidden claims and includes evidence sufficiency logic.

---

## 22. Known Limitations (document in UI/report)
- Attribution is *inferred*; accuracy depends on FPS, resolution, pose, occlusion, audio quality.
- Video-in-video / mirrored sources and recorded playback cannot be distinguished from live speakers in the MVP.
- Overlap detection without diarization is heuristic.
- Whisper text may be wrong; word counts and WPM inherit ASR error.
- Landmark quality varies with demographics, facial hair, glasses, masks, lighting; results should be evaluated per stratum before high-stakes use.
- Confidence values are uncalibrated until the calibration step in §18.4 is completed.
