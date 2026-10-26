# 13 — Speech & Prosody Analysis

**Project:** NTS Meeting Analysis  **Status:** Design spec (implementation-ready)  **Feature version:** `speech_v1`
**Depends on:** `03_DATABASE_SCHEMA`, Phase 6 (job orchestration), Phase 8/9 (faster-whisper STT + speaking turns), `participant_tracks`
**Feeds:** `14_LISTENER_ANALYSIS` (speaker segments and turns), Phase 10 LLM reports (new "Speech & Interaction" section)

> **Assumptions to verify against the real repo before coding** (this spec was written from `project_history_summary.md`, not from the code):
> **A1** `feature_extractions` can hold time-series rows keyed by `(meeting_id, participant_track_id, feature_type, t_start, t_end, payload JSONB)`. If not, use the fallback table in §10.
> **A2** The Phase 8/9 STT output already stores diarized segments and a mapping from diarization label → `participant_track_id`. If word-level timestamps are not stored, re-run `faster-whisper` with `word_timestamps=True` (one-time cost).
> **A3** The audio track is extracted to 16 kHz mono WAV by the STT worker and can be reused.

---

## 0. Principles

| # | Principle |
|---|-----------|
| P1 | **Four strict layers:** RAW → AGGREGATED → DERIVED → LLM INTERPRETATION. Each stored value carries `layer` and `label_type`. |
| P2 | **Label type tags:** `[OBS]` measured directly from audio/transcript; `[INF]` rule-based inference from observations (cautious, with confidence); `[INT]` LLM narrative (never stored as a fact). |
| P3 | **No cross-speaker comparison of raw pitch/loudness.** Pitch depends on physiology, microphone, gain and distance. Prosody is interpreted only **relative to the same speaker's own baseline in the same meeting.** |
| P4 | **Linguistic features come from transcripts only.** Acoustic features never feed sentiment, hedging, agreement, etc. |
| P5 | **Null, not zero.** If a feature cannot be measured reliably (too little voiced audio, too few words) it is `null` with a `reason`, never 0. |
| P6 | **Deterministic, versioned, idempotent.** Same input + `config_hash` ⇒ same output; results UPSERT by `(meeting_id, feature_version)`. No re-transcription, no re-diarization. |
| P7 | **Forbidden interpretations** (enforced in code, prompts and UI copy): pitch, loudness, pace, pauses or fillers must never be described as evidence of confidence, dominance, honesty/deception, intelligence, stress, anxiety, competence or personality. Allowed phrasing: *"pitch varied more than this speaker's own average"*, *"spoke faster than their own baseline in this segment"*. |

---

## 1. Pipeline Position

```
upload → cv_extraction ─┐
                        ├→ feature_fusion → speech_analysis (THIS DOC) → listener_analysis (doc 14) → llm_report → annotated_video
upload → stt/diarization┘
```

* New ARQ job `speech_analysis_worker` registered in `job_service.py`; cascade trigger = success of STT job (parallel to CV).
* Idempotency key: `speech_analysis:{meeting_id}:{feature_version}:{config_hash}`.
* Stages inside the job (each checkpoints to DB so a retry resumes): `prepare → linguistic → pauses/turns/interactions → prosody(audio) → aggregate → derive → persist`.
* Prosody is the only CPU-heavy stage; run per-speaker in a `ProcessPoolExecutor` (Praat releases little of the GIL).

---

## 2. Input Contract

### 2.1 Diarized segment (from STT)

```python
class SpeechSegmentIn(BaseModel):
    segment_id: UUID
    participant_track_id: UUID | None   # None = unmapped speaker
    speaker_id: str                     # diarization label, e.g. "SPEAKER_01"
    start_time: float                   # seconds on the media clock
    end_time: float
    transcript: str
    confidence: float | None            # ASR avg logprob mapped to 0-1, or diarization confidence
    words: list[Word] | None            # [{w, start, end, prob}]  (strongly recommended)
```

### 2.2 Speaker → track mapping (`speaker_track_map`)

`speaker_id → participant_track_id, method ('av_sync'|'manual'|'single_speaker'), confidence`. Unmapped speakers are analysed as pseudo-participants (`track_id = NULL`, `speaker_id` retained) and excluded from person-level joins with CV. Segments with mapping confidence < 0.5 are flagged `low_mapping_confidence` and excluded from cross-modal (doc 14) use.

### 2.3 Audio
`meeting_audio.wav` (16 kHz, mono, PCM16) from MinIO. If per-participant audio channels exist (e.g. bot recordings), prefer them: they make overlap prosody valid.

---

## 3. Preprocessing

### 3.1 Segment cleaning
1. Sort by `start_time`; clamp to `[0, media_duration]`; drop `end ≤ start`, or zero-word segments with duration < 0.2 s (kept as `non_speech_event` if transcript matches `[laughter]`, `[music]`).
2. **Same-speaker overlaps/duplicates** (common in Whisper windows): merge if intervals intersect or gap < 0.05 s.
3. Normalise text: NFKC, collapse whitespace, keep punctuation (needed for sentence/question detection) and case (needed for NER/proper nouns).
4. **Word timeline:** if `words` missing, distribute linearly by character count (`words_source='interpolated'`, pause features become `null`).

### 3.2 Activity timeline (interval algebra)
For each participant *p*: `U_p` = union of merged segment intervals (or, better, union of **word-anchored speech spans**: word i to word i+1 if gap < `min_pause`). Then:

```
A(t)      = { p : t ∈ U_p }           # active speaker set
solo(t)   = |A(t)| == 1
overlap(t)= |A(t)| >= 2
```
Implement with a sorted sweep (O(n log n)) or a 100 Hz boolean grid (`np.zeros((n_speakers, T*100), bool)`); the grid is simpler and is reused by prosody masking.

### 3.3 Backchannel detection (needed before turns/interruptions)
A segment is a **backchannel** if `duration ≤ 1.2 s` **and** `words ≤ 3` **and** normalised text ∈ `BACKCHANNELS` (`yeah, yes, yep, mm-hmm, mhm, uh-huh, right, okay, ok, sure, exactly, i see, got it, true, cool, wow, oh, ah`) **and** it overlaps or immediately follows (≤ 1 s) another speaker's speech. Backchannels are **not** turns, never count as interruptions, but are counted (`backchannels_given/received`).

### 3.4 Turn construction
A **turn** = maximal run of one speaker's non-backchannel segments such that consecutive segments are separated by ≤ `turn_merge_gap` (default 2.0 s) **and** no other speaker's non-backchannel speech starts in between.

```python
def build_turns(segments):
    turns, cur = [], None
    for s in sorted(segments, key=lambda s: s.start):
        if s.is_backchannel: continue
        if cur and s.speaker == cur.speaker and s.start - cur.end <= TURN_MERGE_GAP \
           and not other_speaker_started_between(cur.end, s.start, s.speaker):
            cur.end = max(cur.end, s.end); cur.segments.append(s)
        else:
            if cur: turns.append(cur)
            cur = Turn(speaker=s.speaker, start=s.start, end=s.end, segments=[s])
    if cur: turns.append(cur)
    return [t for t in turns if t.end - t.start >= MIN_TURN_S]   # 0.5 s
```

### 3.5 Audio preparation
* Load with `soundfile`, float32. Estimate noise floor = 10th percentile of frame RMS (dB); `snr_db = p90_rms_db − noise_floor_db`.
* `speech mask` per participant = `U_p ∧ solo(t)` for prosody (**overlap frames excluded from pitch/energy**, kept for rate/pause features). Dilate/erode by 30 ms to avoid boundary artefacts.

---

## 4. RAW FEATURES

Raw features are per-frame, per-word, per-segment or per-event. Everything here is `[OBS]`.

### 4.1 Per-frame acoustic (10 ms hop; solo-speech frames only)

| Field | Method | Notes |
|---|---|---|
| `f0_hz`, `voiced` | Praat autocorrelation via `parselmouth`: `snd.to_pitch_ac(time_step=0.01, pitch_floor=F_lo, pitch_ceiling=F_hi, very_accurate=False)` | **Two-pass per speaker** (Hirst & De Looze): pass 1 with 60–600 Hz; `q1,q3` of voiced f0; pass 2 with `floor = 0.75·q1`, `ceiling = 2.5·q3` to cut octave errors. Fallback `librosa.pyin` only if parselmouth unavailable. |
| `f0_st` | `12·log2(f0_hz / ref_hz)`, `ref_hz` = speaker's median f0 across the meeting | Perceptually scaled; used for variance/range/contour. Speaker-normalised by construction. |
| `rms_db` | `20·log10(sqrt(mean(x²)) + 1e-10)`, 25 ms window, 10 ms hop | Relative dBFS, **not** SPL. |
| `intensity_db` | `snd.to_intensity(minimum_pitch=F_lo, time_step=0.01)` | Praat's smoothed intensity; used for syllable nuclei. |
| `speech_flag` | VAD: faster-whisper's Silero VAD (ONNX, already installed) run on the audio; energy-gate fallback `rms_db > noise_floor + 6 dB` | Frame-level bool. |
| `syllable_nucleus` | de Jong & Wempe (2009): intensity peaks ≥ 2 dB above median, with dip ≥ 2 dB to previous peak, and voiced | Gives syllable timestamps without forced alignment. |

**Octave-jump cleanup:** median filter (5 frames) on voiced runs; drop frames where `|f0_st − running_median(0.5 s)| > 9 st`; require voiced runs ≥ 50 ms.

### 4.2 Per-word (from ASR)
`word, start, end, prob, is_filled_pause, is_repeat, syllables` (syllable count via `pyphen` hyphenation, else vowel-group heuristic `len(re.findall(r'[aeiouy]+', w))`, min 1).

### 4.3 Per-segment raw record

```
segment_id, participant_track_id, start, end, duration, word_count, syllable_count,
words_per_min_seg, syllables_per_sec_seg, articulation_rate_seg,
pause_count_seg, pause_total_s_seg, long_pause_count_seg,
f0_voiced_frames, f0_median_hz, f0_mean_hz, f0_std_st, f0_p5_st, f0_p95_st, f0_slope_st_per_s, f0_terminal_slope_st_per_s,
f0_contour_10hz[]          # semitone series at 10 Hz (downsampled), null-padded for unvoiced
rms_mean_db, rms_std_db, rms_p10_db, rms_p90_db, intensity_mean_db,
voiced_ratio, speech_ratio, snr_db, overlap_fraction, prosody_quality (0-1),
asr_confidence, text_features{...} (see §7)
```

### 4.4 Raw events

| Event | Fields |
|---|---|
| `pause` | `participant_track_id, start, end, duration, position ('clause_boundary'|'mid_clause'|'turn_initial'), adjacent_filler(bool), turn_id` |
| `overlap` | `a_track, b_track, start, end, duration, initiator_track_id` |
| `interruption_candidate` | see §5.4 |
| `backchannel` | `giver_track, receiver_track, time, text` |
| `transition` | `from_track, to_track, gap_s (negative = overlap), turn_from_id, turn_to_id, after_question(bool)` |
| `dialogue_act` | `segment_id, sentence_idx, act, confidence, span` (§7) |

**Pause detection (word-anchored):**
```
for consecutive words w_i, w_{i+1} in the SAME turn:
    gap = w_{i+1}.start − w_i.end
    if gap >= MIN_PAUSE (0.30 s):   # Whisper word times jitter ≈ ±0.1 s; do not go below 0.25 s
        emit pause(w_i.end, w_{i+1}.start)
        position = 'clause_boundary' if w_i.text ends with [.,;:?!—] else 'mid_clause'
```
Gaps **between turns** are *transition gaps / response latency*, not pauses.

---

## 5. AGGREGATED FEATURES

Notation: `p` participant; `U_p` union of speaking intervals; `T_p=|U_p|` (s); `T_meet` meeting duration; `W_p` word count; `Sy_p` syllables; `Turns_p` turns; `P_p` pauses; `M=T_meet/60`. All `[OBS]` unless stated. **Pool frames, do not average per-segment means** for pitch/energy (see §5.6).

### 5.1 Time-and-turn features (items 1–6)

| ID | Feature | Formula | Null when |
|---|---|---|---|
| S01 | `speaking_duration_s` | `T_p` | – |
| S02 | `speaking_share` / `occupancy_ratio` | `T_p / Σ_q T_q` and `T_p / T_meet` | `T_meet<=0` |
| S03 | `turn_count` | `|Turns_p|` | – |
| S04 | `avg_turn_duration_s` (+median, p90) | `mean(dur(turn))` | `turn_count=0` |
| S05 | `longest_turn_s` (+turn_id) | `max dur` | same |
| S06 | `shortest_turn_s` | `min dur` among turns ≥ `MIN_TURN_S` | same |

### 5.2 Rate & pause features (items 7–11)

| ID | Feature | Formula |
|---|---|---|
| S07 | `words_per_min` (gross) | `W_p / (T_p/60)` — includes pauses inside turns |
| S08a | `speaking_rate_syl_per_s` (gross) | `Sy_p / T_p` |
| S08b | `articulation_rate_syl_per_s` | `Sy_p / (T_p − Σ pause_dur)` — excludes pauses |
| S08c | `words_per_sec` | `W_p / T_p` |
| S09 | `pause_frequency_per_min` | `|P_p| / (T_p/60)` |
| S10 | `avg_pause_s` (+median, p90) | `mean(dur)` |
| S11 | `long_pause_count`, `long_pause_rate_per_min`, `very_long_pause_count` | pauses ≥ 1.0 s / ≥ 2.0 s |

### 5.3 Lexical features (items 12–17; details in §7)

| ID | Feature | Formula |
|---|---|---|
| S12 | `filler_count_strict` / `_broad` | filled pauses (+ repetitions) / + context-checked discourse fillers |
| S13 | `filler_per_100_words`, `filler_per_min` | `100·F/W_p`, `F/(T_p/60)` |
| S14 | `sentence_len_mean/median/p90/max` (words) | sentence split by `pysbd` on segment text, joined across segments of a turn |
| S15 | `mattr_50`, `mtld`, `guiraud_r`, `hapax_ratio` | `MATTR` = mean TTR over sliding windows of 50 tokens; `Guiraud = V/√N`. **Do not use raw TTR** (length-biased). Null if `W_p < 100`. |
| S16 | `question_count`, `questions_per_min`, `question_ratio` | `Q / sentences` |
| S17 | `sentence_type_dist` | fractions of `statement / question / imperative_or_proposal / exclamation / fragment` |

### 5.4 Interaction features (items 18–22)

**Interruption candidate algorithm** (labels are `[INF]`; name is *candidate*, never "rude"):

```python
for B in non_backchannel_segments:
    A = segment_active_at(B.start, exclude=B.speaker)         # someone holding the floor
    if not A or A.start > B.start - 0.05: continue
    ov = min(A.end, B.end) - B.start
    if ov < MIN_OVERLAP (0.3 s): continue                      # ignore ASR/diarization jitter
    if abs(A.start - B.start) <= 0.3: kind = 'simultaneous_start'
    elif A.end - B.start <= 0.5: kind = 'anticipatory_transition'   # ends near TRP → not an interruption
    elif is_short_agreement(B): kind = 'cooperative_overlap'
    else: kind = 'interruption_candidate'
    outcome = 'yielded' if speech_of(A.speaker) absent for [B.start+YIELD_WIN(2.0 s)−1.0, B.start+YIELD_WIN] \
              else 'held_floor'
    conf = min(1, ov/1.0) * mapping_conf(A,B) * diar_conf(B)
```

| ID | Feature | Formula |
|---|---|---|
| S18 | `interruptions_made`, `_received`, `per_10min`, `success_rate` | count of `interruption_candidate` with B/A = p; `success = yielded / made` |
| S19 | `overlap_time_s`, `overlap_ratio`, `overlaps_initiated/received`, `overlap_share_cooperative` | `|U_p ∩ ⋃_{q≠p} U_q|`, `/T_p` |
| S20 | `response_latency_s` median/mean/p90; `share_overlapping (gap<0)`, `share_fast (<0.2 s)`, `share_slow (>1.0 s)`; `latency_after_question_s` | for each transition q→p: `gap = start(turn_p) − end(turn_q)`; keep gaps in `[−2, +10]`; report distribution as speaker **p** (responder). Latency is `[OBS]`; diarization timing error ±0.2 s ⇒ don't report < 0.2 s differences. |
| S21 | `turns_per_min`, `transitions_in/out_per_min` | `Turns_p/M` etc. |
| S22 | Transition matrix | `T[i][j]` counts of i→j (i≠j); `P[i][j]=T[i][j]/Σ_k T[i][k]`; also top-5 bigram sequences (A→B→A ping-pong count), matrix entropy `H = −ΣP log P`, reciprocity `Σ min(T_ij,T_ji)/ΣT`. |

### 5.5 Prosodic aggregates (items 23–35)

Pool voiced solo frames of participant p across all segments → set `F_p`. Require `|F_p| ≥ 300` frames (3 s voiced) else null (`reason='insufficient_voiced_audio'`).

| ID | Feature | Formula / method |
|---|---|---|
| P23 | `f0_hz` stream | §4.1 (raw stream stored at 10 Hz) |
| P24 | `f0_mean_hz` (arith), `f0_geomean_hz` | `mean(F_p)`; `exp(mean(ln f0))` |
| P25 | `f0_median_hz` | median of pooled frames (or from histogram, §5.6) |
| P26 | `f0_std_st`, `f0_var_hz2` | std of `f0_st`; **semitones preferred** |
| P27 | `f0_range_st` (p95−p5), `f0_range_hz`, `f0_min/max` | robust range; min/max stored but flagged as outlier-prone |
| P28 | `contour_*`: `mean_abs_delta_st_per_s`, `slope_st_per_s`, `terminal_slope_st_per_s` (last 300 ms of voiced speech per utterance), `contour_dct[1..5]` | contour at 10 Hz; slope = OLS; terminal slope kept as **raw** feature only (not used to classify questions) |
| P29 | `energy_mean_db`, `energy_p10/p90_db`, `energy_dynamic_range_db (p90−p10)` | pooled `rms_db` over `speech_flag ∧ solo` frames |
| P30 | `energy_std_db` | std of pooled `rms_db` |
| P31 | `intensity_mean_db`, `intensity_rel_db` | Praat intensity mean; `rel = mean − speaker meeting median` at segment level. Label "relative level", not "volume/loudness of voice". |
| P32 | `voice_activity_ratio` = `T_p / T_meet`; `phonation_ratio` = voiced_frames / speech_frames in `U_p`; `meeting_speech_ratio` = `|⋃U_p| / T_meet`; `silence_ratio = 1 − that` | – |
| P33 | `rhythm_npvi`, `isi_cv` | `ISI_k` = inter-syllable-nucleus intervals (s), only within same turn & gaps < 0.4 s. `nPVI = 100/(m−1) · Σ |ISI_k − ISI_{k+1}| / ((ISI_k+ISI_{k+1})/2)`; `ISI_cv = std/mean`. Null if < 30 intervals. |
| P34 | `rate_cv`, `rate_iqr`, `rate_slope_within_turn`, `rate_change_points` | syllable rate in 3 s windows / 1 s hop within turns (`Sy_window/ speech_time_window`); `cv = std/mean`; per-turn OLS slope of windowed rate |
| P35 | `pause_structure`: histogram bins `[0.3–0.5, 0.5–1, 1–2, >2]`, `pause_time_ratio = ΣP/T_p`, `share_mid_clause`, `share_adjacent_filler`, `pause_cv`, `burstiness B=(σ−μ)/(σ+μ)`, `turn_initial_silence_median` | B ∈ (−1,1): −1 regular, 0 Poisson-like, →1 bursty |

### 5.6 Time aggregation rules

1. **Duration-weighted, not mean-of-means.** `rate = ΣSy / ΣT`, never `mean(rate_seg)`.
2. **Pitch/energy pooling via histograms:** store per participant per window a histogram of `f0_st` (0.25 st bins, −36…+36 st) and `rms_db` (0.5 dB bins). Meeting/person stats (mean, median, percentiles, variance) are recomputed from summed histograms → exact re-aggregation for any window without re-reading audio.
3. **Windows** (all stored in `speech_windows`): `per_segment`, `per_turn`, `sliding 30 s / 10 s hop` (person-level and meeting-level), `per_minute`. Window features: speaking share, wpm, pauses/min, f0_std_st, energy_std, overlap ratio, interruptions, questions, sentiment mean, act counts.
4. **Meeting phases:** optional split into thirds (`start / middle / end`) to expose drift; do not interpret drift.
5. **Minimum support** table (below this ⇒ null): pitch 3 s voiced; MATTR 100 words; rate 10 s speech; response latency ≥ 3 transitions; nPVI 30 intervals; sentiment ≥ 20 words.

### 5.7 Meeting-level aggregates

`participants_speaking`, `total_speech_s`, `silence_ratio`, `overlap_ratio_meeting = |overlap(t)|/|⋃U|`, `turns_total`, `turns_per_min`, `transitions_per_min`, `median_transition_gap_s`, `interruption_candidates_per_10min`, `backchannels_per_min`, `mean_turn_duration_s`, `monologue_turns (>60 s)`, `question_ratio_meeting`, `decision_count`, `action_item_count`, `speech_data_quality_score`.

---

## 6. DERIVED FEATURES

All `[INF]`. Each has `formula`, `evidence[]` (raw/aggregate keys used), `confidence`, `caveats`. None is a trait or psychological state.

| ID | Derived feature | Formula | Cautious label output |
|---|---|---|---|
| D01 | `participation_balance` | Gini of `T_p`; normalised entropy `H/ln(n)`; `max_share` | "Talk time was concentrated in N participant(s)" |
| D02 | `talk_share_z` | `(T_p − mean)/std` across participants | descriptive only |
| D03 | `pitch_movement_rel` | `f0_std_st(segment) / median_over_speaker_segments(f0_std_st)` → bins `<0.75 lower`, `0.75–1.25 typical`, `>1.25 higher` "than this speaker's own typical" | never compared across speakers |
| D04 | `pace_rel` | `articulation_rate(segment) / speaker_median` → same bins | "faster/slower than own baseline" |
| D05 | `pace_shift_events` | change-point (rolling z of windowed rate, `|z|>2` for ≥ 5 s) | timestamps only |
| D06 | `disfluency_index` | `0.4·z(filler_per_100w) + 0.3·z(mid_clause_pause_rate) + 0.3·z(repetition_rate)`, z within meeting, clipped | "more/less disfluent-like speech than others in this meeting" — **not hesitation, nervousness or uncertainty** |
| D07 | `conversation_interactivity` | `z(transitions/min) + z(overlap_ratio) − z(median_gap)` | "fast-paced exchange" vs "slow-paced" |
| D08 | `turn_network` | directed graph from `T`; density, reciprocity, hub score (weighted in-degree), `who_responds_to_whom` top edges | descriptive |
| D09 | `question_response_rate` | `P(next turn by another speaker starts ≤ 3 s after a question)`; also `unanswered_questions` | descriptive |
| D10 | `stance_ratio` | `(assertive_per_100w + 1)/(hedge_per_100w + uncertainty_per_100w + 1)` (log) | "more hedged than assertive *wording*" |
| D11 | `collaboration_language_rate` | `(agree + ack + proposal + clarification_req) per 100w` | wording only |
| D12 | `decision_flow` | ordered chain *proposal → agreement* → *decision* within 120 s; `time_to_decision` | list of events with timestamps |
| D13 | `monologue_flags` | turns > 60 s with no backchannel from others | timestamps |
| D14 | `prosody_reliability` | `0.4·min(1,voiced_s/30) + 0.3·snr_factor + 0.3·(1−overlap_share)`; `snr_factor = clip((snr_db−5)/20,0,1)` | attached to every prosodic derived value |

**Confidence rule** for any `[INF]` item: `conf = base(evidence) × min(sample_support, 1) × quality`; if `conf < 0.4` the item is stored but hidden by default in the UI.

---

## 7. LINGUISTIC FEATURES (transcript only)

### 7.1 Method stack
* **Tokenisation / sentences:** `pysbd` (rule-based, tiny). **NLP:** `spaCy en_core_web_sm` (POS for filler disambiguation, `DATE`/`PERSON` NER for action items). Both run on CPU in the current container.
* **Matching:** `spacy.matcher.PhraseMatcher` / compiled regex per category, negation window of 3 tokens (`not, n't, never, no`).
* **Sentiment:** `vaderSentiment` compound per sentence (fast, no model download). Optional upgrade: a small ONNX sentiment model behind a feature flag.
* **Emotional language:** curated in-repo lexicon `emotion_lexicon.json` (categories below). NRC EmoLex is optional — **check its licence before commercial use.**
* **Ambiguous cases** (optional Stage 2, feature-flagged): batch low-confidence sentences to the existing Groq model for `dialogue_act` labelling with a strict JSON schema; store with `source='llm'` and `label_type='inference'`.

### 7.2 Feature catalogue (each is multi-label per sentence with `confidence`)

| Feature | Definition / patterns (examples; extend in `lexicons/*.yaml`) | Confidence |
|---|---|---|
| `sentiment` | VADER compound ∈ [−1,1]; label pos ≥ 0.05, neg ≤ −0.05 | `abs(compound)` scaled; null if < 3 tokens |
| `emotional_language` | lexicon hits per category: `enthusiasm, frustration, concern, gratitude, appreciation, amusement, sadness, anger, anxiety_words` (rate per 100 w) | hit-density based; word-level, not speaker-state |
| `uncertainty_marker` | epistemic-uncertainty phrases: *not sure, don't know, no idea, unclear, uncertain, might be, could be, probably, possibly, I'm not certain* | 0.7 (0.5 if in question) |
| `hedge` | softeners: *kind of, sort of, maybe, perhaps, I guess, a bit, somewhat, I was wondering if, it seems, just (minimiser), I think (weak 0.4)* | 0.4–0.8 by phrase |
| `assertive` | boosters/commitment: *definitely, absolutely, certainly, clearly, for sure, we must, we need to, have to, I will, we will, let's, I'm confident, no doubt* | 0.6–0.8 |
| `agreement` | sentence-initial *yes, yeah, right, exactly, agreed, I agree, that makes sense, good point, sounds good, absolutely* (not negated) | 0.8 initial, 0.5 elsewhere |
| `disagreement` | *I disagree, I don't think so, not really, that's not, I'm not sure that's, but actually, on the other hand, no,* (sentence-initial) | 0.8; contrastive *but* alone = 0.3 |
| `acknowledgment` | *okay, got it, I see, understood, noted, thanks, thank you, alright* | 0.7 |
| `question` | `?` from ASR **or** wh-word/aux-inversion at sentence start (`what, why, how, who, when, where, which, can you, could you, do you, are we, is it, would it`) or tag (*right?, isn't it?*) | 0.9 if `?`+syntax; 0.6 syntax only |
| `proposal` | *let's, how about, what if we, we could, we should, I suggest, I propose, my suggestion, why don't we, shall we, maybe we can* | 0.75 |
| `decision` | *we'll go with, let's go with, we decided, decision is, final call, agreed then, that's settled, we're going ahead, approved, ship it* | 0.8; boosted if preceded by proposal/agreement within 60 s |
| `clarification_request` | *what do you mean, can you clarify, could you repeat, sorry?, I didn't get, can you explain, do you mean, just to confirm, to be clear* | 0.8 |
| `summary` | *to summarize, in summary, so basically, so what we have, to recap, in short, so far we've, the takeaway is, so overall* | 0.75 |
| `action_item` | (`I'll|I will|we will|you will|can you|could you|please|needs to|should` + verb) **and** (owner: PERSON/participant name/pronoun) **and/or** (deadline: spaCy `DATE`, *by Friday, tomorrow, EOD, next week*); keywords *action item, follow up, take this, own this* | 0.5 verb-only, 0.8 with owner+deadline |

**Addressee hint:** if a participant display name (from `participants`) appears as a vocative in a question/action sentence → `addressee_track_id` (`[INF]`, conf 0.7).

### 7.3 Filler handling
```
FILLED_PAUSES   = {um, umm, uh, uhh, er, erm, ah, hmm, mm}          # unambiguous
DISCOURSE_FILL  = {"you know", "i mean", "like", "sort of", "kind of", "basically", "actually", "literally", "right"}
```
* `filler_strict` = filled pauses + immediate word repetitions ("the the", "I I") + false-start markers (`--` or truncated tokens).
* `filler_broad` = strict + `DISCOURSE_FILL` occurrences that pass the POS rule: *"like"* counts only if not VERB/ADP/SCONJ/comparative (`spaCy pos_` ∉ {VERB, ADP}) and sentence-medial without a following noun phrase; *"you know/I mean"* only if set off by commas/pauses; *"right"* only if not in `agreement`.
* **ASR caveat:** Whisper drops many fillers by default. Mitigations: pass `initial_prompt="Um, uh, so, like, you know, I mean, hmm."` to faster-whisper and disable `condition_on_previous_text` for disfluency-focused runs. Set `filler_reliability='low'` when the meeting-wide strict filler rate is < 0.2 per 100 words, and show a warning in the UI.

### 7.4 Aggregation of linguistic features
* Segment → count and per-100-word rate per label; participant → Σcounts / Σwords; meeting → same plus **event timeline** (`decision`, `action_item`, `proposal`, `disagreement`, `clarification_request`) with timestamps and speaker.
* `sentiment_mean` = word-weighted mean of sentence compounds; `sentiment_volatility` = std of sentence compounds; `share_pos/neg/neutral`.

---

## 8. Pseudocode (orchestrator)

```python
async def speech_analysis_worker(ctx, meeting_id, config=DEFAULT):
    run = start_run(meeting_id, config)                        # UPSERT run row, status=running
    segs, words, audio_path = load_inputs(meeting_id)          # A2/A3
    segs = clean_segments(segs)                                # §3.1
    timeline = build_activity_grid(segs)                       # §3.2
    segs = tag_backchannels(segs, timeline)                    # §3.3
    turns = build_turns(segs)                                  # §3.4

    # Linguistic (pure text, cheap)
    ling = [extract_linguistic(s) for s in segs]               # §7

    # Timing / interaction
    pauses = detect_pauses(words, turns)
    inter  = classify_overlaps_and_interruptions(segs, timeline)
    trans  = compute_transitions(turns, ling)                  # gap, after_question
    persist_events(run, pauses, inter, trans)

    # Prosody (CPU heavy)
    audio, sr = sf.read(audio_path, dtype='float32')
    noise_floor = estimate_noise_floor(audio, sr)
    prosody = {}
    with ProcessPoolExecutor() as ex:
        for spk in speakers:
            mask = timeline.solo_mask(spk)
            prosody[spk] = ex.submit(extract_prosody, audio, sr, segs_of(spk), mask, noise_floor)
    prosody = {k: v.result() for k, v in prosody.items()}

    # Aggregate → derive
    seg_feats  = merge_segment_features(segs, ling, pauses, prosody)
    person     = aggregate_persons(seg_feats, turns, pauses, inter, trans, prosody.histograms)
    meeting    = aggregate_meeting(person, turns, trans, timeline)
    windows    = build_windows(seg_feats, [30, 10], per_minute=True)
    derived    = derive_features(person, meeting, windows)
    persist_all(run, seg_feats, person, meeting, windows, derived)
    enqueue_next(meeting_id, 'listener_analysis')

def extract_prosody(audio, sr, segs, mask, noise_floor):
    snd = parselmouth.Sound(audio, sr)
    f0_pass1 = snd.to_pitch_ac(0.01, 60, 600)
    q1, q3 = voiced_quartiles(f0_pass1, mask)
    pitch = snd.to_pitch_ac(0.01, 0.75*q1, 2.5*q3, very_accurate=False)
    inten = snd.to_intensity(minimum_pitch=0.75*q1, time_step=0.01)
    f0 = clean_octave_jumps(pitch.selected_array['frequency'], mask)
    ref = np.nanmedian(f0[f0 > 0]);  f0_st = 12*np.log2(f0/ref)
    rms = frame_rms_db(audio, sr, win=0.025, hop=0.01)
    nuclei = detect_syllable_nuclei(inten, pitch)             # de Jong & Wempe
    per_seg = [segment_stats(seg, f0_st, rms, inten, nuclei, mask) for seg in segs]
    hist = {'f0_st': hist_025st(f0_st[mask & voiced]), 'rms_db': hist_05db(rms[mask & speech])}
    return Prosody(ref_hz=ref, per_seg=per_seg, hist=hist, series_10hz=downsample(f0_st, rms))

def aggregate_persons(...):
    for p in participants:
        T = union_duration(p); W = words(p); Sy = syllables(p)
        m = {'speaking_duration_s': T, 'wpm': W/(T/60) if T>=10 else None,
             'articulation_rate': Sy/(T-pause_time(p)) if T-pause_time(p)>=10 else None, ...}
        h = sum_histograms(prosody_of(p))                   # exact pooled percentiles
        m |= f0_stats_from_hist(h) if voiced_frames(h) >= 300 else null_with_reason('insufficient_voiced_audio')
        ...
```

**Question detection (used by S16/S17):**
```python
def sentence_type(sent):
    t = sent.strip().lower()
    if t.endswith('?') or QUESTION_START.match(t) or TAG_QUESTION.search(t): return 'question'
    if IMPERATIVE_START.match(t) or PROPOSAL.search(t): return 'imperative_or_proposal'
    if t.endswith('!'): return 'exclamation'
    if len(t.split()) < 3: return 'fragment'
    return 'statement'
```

---

## 9. Libraries & Docker

Add to `backend/requirements.txt` (all pip-installable wheels; no GPU needed):

| Purpose | Library | Notes |
|---|---|---|
| Numerics | `numpy`, `scipy`, `pandas` | probably present |
| Audio I/O | `soundfile` (needs `libsndfile1` apt package) | ffmpeg already available |
| Pitch/intensity/formant | `praat-parselmouth` | manylinux wheels, ~15 MB; primary pitch tracker |
| Fallback pitch | `librosa` (pyin) | **optional**: heavy (`numba`); skip unless parselmouth fails |
| VAD | reuse Silero via `faster-whisper` (`onnxruntime`) | no new dependency |
| Loudness (optional) | `pyloudnorm` | integrated LUFS for reports only |
| Sentence split | `pysbd` | |
| NLP | `spacy` + `en_core_web_sm` (`python -m spacy download en_core_web_sm` in Dockerfile) | disable unused pipes: `nlp = spacy.load(..., disable=['lemmatizer'])` |
| Sentiment | `vaderSentiment` | |
| Syllables | `pyphen` | fallback regex heuristic |
| Lexical diversity | own `mattr()`/`mtld()` (30 lines) or `lexicalrichness` | |
| Validation | `pydantic` v2 | existing |

Dockerfile additions: `apt-get install -y libsndfile1` and the spaCy model layer. Memory: full-meeting WAV at 16 kHz mono float32 = 230 MB/hour → process per-speaker masks lazily; for meetings > 2 h use chunked reads (`soundfile.blocks`) and stitch histograms.

**Runtime budget (target):** 1 h meeting, 4 speakers ≈ 60–120 s CPU (Praat pitch ≈ 0.05× real-time per speaker).

---

## 10. Database Fields

All new tables are UUID-keyed with `organization_id` (RLS simulation via `get_current_org`) and `run_id → speech_analysis_runs`. Use Alembic migration `add_speech_analysis`.

```sql
CREATE TABLE speech_analysis_runs (
  id UUID PRIMARY KEY, meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  feature_version TEXT NOT NULL, config_hash TEXT NOT NULL, config JSONB NOT NULL,
  status TEXT NOT NULL, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
  quality JSONB,                       -- snr_db, asr_conf_mean, mapping_conf_mean, filler_reliability, warnings[]
  UNIQUE (meeting_id, feature_version)  -- UPSERT target
);

CREATE TABLE speaker_track_map (
  meeting_id UUID, speaker_id TEXT, participant_track_id UUID REFERENCES participant_tracks(id),
  method TEXT, confidence REAL, PRIMARY KEY (meeting_id, speaker_id)
);

CREATE TABLE speech_turns (
  id UUID PRIMARY KEY, run_id UUID, meeting_id UUID, participant_track_id UUID, speaker_id TEXT,
  start_time REAL, end_time REAL, duration REAL, word_count INT, segment_ids UUID[],
  ends_with_question BOOL, overlap_fraction REAL, seq_index INT
);
CREATE INDEX ON speech_turns (meeting_id, start_time);

CREATE TABLE speech_segment_features (        -- one row per STT segment
  segment_id UUID PRIMARY KEY, run_id UUID, meeting_id UUID, participant_track_id UUID, turn_id UUID,
  start_time REAL, end_time REAL, is_backchannel BOOL,
  word_count INT, syllable_count INT, wpm REAL, articulation_rate REAL,
  pause_count INT, pause_total_s REAL, long_pause_count INT,
  filler_strict INT, filler_broad INT, mean_sentence_len REAL, question_count INT,
  sentiment REAL, hedge_count INT, uncertainty_count INT, assertive_count INT,
  f0_median_hz REAL, f0_mean_hz REAL, f0_std_st REAL, f0_p5_st REAL, f0_p95_st REAL,
  f0_slope REAL, f0_terminal_slope REAL, rms_mean_db REAL, rms_std_db REAL, intensity_mean_db REAL,
  voiced_ratio REAL, overlap_fraction REAL, snr_db REAL, prosody_quality REAL,
  contour_10hz REAL[],                       -- semitone series; NULL for unvoiced
  extra JSONB                                -- everything else (dct coefficients, per-label counts)
);

CREATE TABLE speech_events (                 -- pauses, overlaps, interruptions, backchannels, transitions
  id UUID PRIMARY KEY, run_id UUID, meeting_id UUID, event_type TEXT,
  participant_track_id UUID, other_track_id UUID, start_time REAL, end_time REAL,
  attributes JSONB, confidence REAL, label_type TEXT DEFAULT 'observation'
);
CREATE INDEX ON speech_events (meeting_id, event_type, start_time);

CREATE TABLE speech_dialogue_acts (
  id UUID PRIMARY KEY, run_id UUID, segment_id UUID, participant_track_id UUID,
  sentence_idx INT, start_time REAL, end_time REAL, act TEXT, confidence REAL,
  source TEXT DEFAULT 'rule', span TEXT, addressee_track_id UUID, attributes JSONB
);

CREATE TABLE speech_participant_metrics (
  run_id UUID, participant_track_id UUID, PRIMARY KEY (run_id, participant_track_id),
  speaking_duration_s REAL, speaking_share REAL, occupancy_ratio REAL, turn_count INT,
  avg_turn_s REAL, longest_turn_s REAL, shortest_turn_s REAL, wpm REAL, articulation_rate REAL,
  pause_per_min REAL, avg_pause_s REAL, long_pause_count INT, filler_per_100w REAL,
  mattr_50 REAL, question_ratio REAL, interruptions_made INT, interruptions_received INT,
  overlap_ratio REAL, response_latency_median_s REAL, turns_per_min REAL,
  f0_median_hz REAL, f0_mean_hz REAL, f0_std_st REAL, f0_range_st REAL,
  energy_std_db REAL, voice_activity_ratio REAL, phonation_ratio REAL, rhythm_npvi REAL,
  metrics JSONB NOT NULL,        -- full nested set incl. distributions, histograms, null reasons
  histograms JSONB,              -- f0_st and rms_db histograms for exact re-aggregation
  derived JSONB,                 -- D01..D14 with evidence/confidence/caveats
  quality JSONB                  -- prosody_reliability, sample supports
);

CREATE TABLE speech_meeting_metrics (run_id UUID PRIMARY KEY, metrics JSONB, derived JSONB, transition_matrix JSONB, timeline_events JSONB);

CREATE TABLE speech_windows (
  run_id UUID, scope TEXT,            -- 'person' | 'meeting'
  participant_track_id UUID NULL, window_type TEXT, t_start REAL, t_end REAL, metrics JSONB
);
CREATE INDEX ON speech_windows (run_id, scope, window_type, t_start);

CREATE TABLE nts_speech_reports (   -- LLM layer; same UPSERT/caching pattern as nts_visual_reports
  meeting_id UUID, run_id UUID, model TEXT, prompt_hash TEXT, report JSONB, pdf_asset_id UUID,
  PRIMARY KEY (meeting_id, prompt_hash)
);
```

**Integration with `feature_extractions`:** persist 10 Hz `f0_st` / `rms_db` / `speech_flag` streams as `feature_extractions` rows (`feature_type='speech_prosody_10hz'`, `participant_track_id`, `t_start/t_end` = 60 s chunks, `payload={dt:0.1, f0_st:[...], rms_db:[...], voiced:[...]}`) so `feature_fusion` and doc 14 read audio and video signals through **one** access path. Fallback if A1 fails: table `speech_prosody_series(run_id, participant_track_id, t_start, dt, f0_st REAL[], rms_db REAL[], voiced BOOL[])`.
Also write headline numbers into `behavioral_metrics` (`metric_family='speech'`) so existing dashboards and `nts_scores` fusion can pick them up unchanged.

---

## 11. API

Base `/api/v1/meetings/{meeting_id}/speech`, JWT + RBAC (`ANALYST+` to run; `USER` read-only). Job status uses the existing `useJobPolling` contract.

| Method & path | Purpose |
|---|---|
| `POST /run` | enqueue `speech_analysis` (idempotent; `?force=true` to bypass cache) → `{job_id}` |
| `GET /summary` | meeting metrics + per-participant headline metrics + quality |
| `GET /participants/{track_id}` | full participant metrics, derived, histograms |
| `GET /segments?from=&to=&track_id=` | segment features (paginated, includes contour if `include=contour`) |
| `GET /timeline?bucket=10&metrics=wpm,f0_std_st,overlap_ratio` | windowed series |
| `GET /events?type=pause,interruption_candidate,decision,action_item` | event lists |
| `GET /transitions` | matrix + bigrams + network edges |
| `GET /linguistic?track_id=` | act counts/rates, sentiment, evidence snippets |
| `GET /report` / `POST /report` | LLM interpretation (cached) |

**Response envelope for every value** (so the UI can render layer/label/confidence generically):

```json
{
  "meeting_id": "…", "run_id": "…", "feature_version": "speech_v1",
  "quality": {"snr_db": 22.4, "asr_confidence_mean": 0.87, "mapping_confidence_mean": 0.93,
              "filler_reliability": "medium", "warnings": ["overlap_prosody_excluded_12pct"]},
  "meeting": {
    "metrics": {"silence_ratio": {"value": 0.14, "unit": "ratio", "layer": "aggregated", "label_type": "observation"},
                "transitions_per_min": {"value": 3.1, "n": 96, "label_type": "observation"}},
    "transition_matrix": {"tracks": ["t1","t2","t3"], "counts": [[0,14,6],[12,0,9],[5,8,0]]},
    "derived": {"participation_balance": {"value": {"gini": 0.31, "max_share": 0.46},
                 "label_type": "inference", "confidence": 0.9,
                 "text": "Talk time was concentrated in one participant.", "evidence": ["S02"]}}
  },
  "participants": [{
    "participant_track_id": "t1", "display_name": "Speaker 1",
    "metrics": {
      "speaking_duration_s": {"value": 842.5, "layer": "aggregated", "label_type": "observation"},
      "speaking_share": {"value": 0.46, "label_type": "observation"},
      "wpm": {"value": 148.2, "n_words": 2081, "label_type": "observation"},
      "pause_per_min": {"value": 11.4, "label_type": "observation"},
      "filler_per_100w": {"value": 2.1, "reliability": "medium", "label_type": "observation"},
      "response_latency_s": {"median": 0.42, "p90": 1.3, "n": 31},
      "f0": {"median_hz": 118.4, "std_st": 2.9, "range_st": 9.8, "voiced_frames": 41210,
             "note": "Compare only with this speaker's own baseline.", "label_type": "observation",
             "quality": 0.91},
      "energy": {"std_db": 5.2, "dynamic_range_db": 14.0, "note": "relative level, uncalibrated microphone"},
      "rhythm": {"npvi": null, "reason": "insufficient_syllable_intervals"}
    },
    "derived": {
      "pitch_movement_rel": {"value": "higher_than_own_typical", "segments": [{"segment_id":"…","ratio":1.4}],
                             "label_type": "inference", "confidence": 0.62,
                             "caveats": ["Relative to this speaker's own average; not evidence of any emotion or state."]}
    },
    "linguistic": {"question_ratio": 0.17, "hedge_per_100w": 1.6, "assertive_per_100w": 0.9,
                   "sentiment_mean": 0.12, "acts": {"proposal": 6, "agreement": 9, "decision": 2, "action_item": 3}}
  }]
}
```

---

## 12. Frontend Requirements

Stack: React + Recharts (existing) + a thin custom SVG layer for swimlanes/heatmaps (no new heavy chart dependency). New route `MeetingAnalysis → Speech` tab; data via `useSpeechAnalysis(meetingId)` hook + `useJobPolling`.

| Component | Content | Notes |
|---|---|---|
| `SpeechQualityBanner` | ASR/diarization/mapping/SNR/filler-reliability warnings | shown first; amber if `prosody_reliability < 0.5` |
| `TalkTimeBar` | stacked bar of `speaking_share` + occupancy % | tooltip shows duration and turn count |
| `SpeakerTimeline` (swimlane) | one lane per participant, blocks = turns; overlays: pauses ≥ 1 s (ticks), overlaps (hatched), interruption candidates (▼), backchannels (dots), decisions/actions (flags) | click → seek video (existing player); brushing zooms all charts |
| `TurnTransitionMatrix` | heatmap of `P[i][j]` with counts; row/col = participants | second view: directed network (node size = turns, edge width = transitions) |
| `PaceChart` | windowed articulation rate lines per participant, own-baseline band (median ± IQR) | y-axis normalised toggle |
| `ProsodyPanel` (per person) | f0 contour sparkline in semitones with own-median line; f0 range violin/histogram; energy histogram; badge "relative to this speaker" | **never overlays two people's Hz on one axis**; no colouring green/red |
| `PauseStructure` | histogram of pause lengths + share mid-clause/boundary; pauses/min | |
| `LatencyDistribution` | box/strip of response latency per responder | annotate n |
| `FillerAndDisfluency` | rate bars with reliability icon | |
| `LinguisticTimeline` | dialogue-act markers per person (proposal, agreement, disagreement, question, decision, action item) + sentiment sparkline | click marker → transcript excerpt |
| `DecisionsAndActions` | table: time, speaker, text, owner, deadline, confidence | export CSV |
| `ParticipantCard` | headline metrics with **OBS / INF / INT** chips, confidence dots, "why?" popover listing evidence keys and caveats | INF items with `conf<0.4` collapsed |
| `LLMInterpretationCard` | LLM narrative, each claim with evidence chips linking to metrics | banner: "Interpretive summary generated by AI from measured features" |

UX rules: never use words *confident, nervous, dominant, aggressive, deceptive*, never colour-code prosody as good/bad, always show `n` and `null` reasons ("not enough voiced audio"), and provide a metric glossary drawer.

---

## 13. LLM Interpretation Layer

* **Inputs:** compact JSON only (person metrics, derived items with confidence, meeting metrics, top 10 timeline events, ≤ 8 short transcript excerpts with timestamps for linguistic evidence). No raw audio, no full transcript. Target ≤ 6 k tokens.
* **System prompt (essentials):**
  1. "You describe *conversation behaviour*, not people's traits or inner states."
  2. "Every statement must cite one or more `evidence` keys present in the input and state whether it is an observation or an inference."
  3. "Forbidden: claims about confidence, dominance, honesty, intelligence, stress, anxiety, mood or personality from pitch, loudness, pace, pauses or fillers."
  4. "Prosodic values are relative to each speaker's own baseline; never compare pitch or loudness between speakers."
  5. "If evidence is missing or confidence < 0.4, say the data is insufficient."
  6. "Return JSON only."
* **Output schema:**
```json
{"meeting_summary": [{"statement": "...", "evidence": ["S02","D01"], "type": "observation|inference"}],
 "participants": [{"participant_track_id": "...", "patterns": [{"statement":"...", "evidence":[...], "type":"inference", "confidence": 0.6}],
                   "limitations": ["..."]}],
 "interaction_dynamics": [...], "data_quality_notes": [...]}
```
* **Validator (post-LLM, mandatory):** (a) JSON schema; (b) each `evidence` key exists in the payload; (c) regex blocklist for forbidden concepts (`confiden|dominan|honest|decepti|nervous|anxious|stress|intellig|personality|aggressive|weak|insecure`) → reject and retry once with the violation named, then fall back to a template summary; (d) claims with `confidence < 0.4` removed. Cache by `prompt_hash` (UPSERT into `nts_speech_reports`). The model used is the one already configured for the Phase 10 Groq pipeline; avoid `response_format=json_object` (known issue) — rely on prompt + validator.

---

## 14. Default Configuration (`speech_config.yaml`)

| Key | Default | Rationale |
|---|---|---|
| `min_pause_s` | 0.30 | ASR word-time jitter ≈ ±0.1 s |
| `long_pause_s` / `very_long_pause_s` | 1.0 / 2.0 | |
| `turn_merge_gap_s` | 2.0 | |
| `min_turn_s` | 0.5 | |
| `backchannel_max_dur_s` / `_max_words` | 1.2 / 3 | |
| `min_overlap_s` | 0.3 | diarization boundary error |
| `interrupt_near_end_tol_s` | 0.5 | anticipatory transition |
| `yield_window_s` | 2.0 | |
| `f0_first_pass` / `f0_step` | 60–600 Hz / 10 ms | |
| `min_voiced_frames` | 300 | 3 s |
| `rate_window_s` / `hop_s` | 3 / 1 | |
| `mattr_window` / `min_words_lexical` | 50 / 100 | |
| `sliding_window_s` / `hop_s` | 30 / 10 | |
| `transition_gap_range_s` | [−2, 10] | |
| `min_conf_display` | 0.4 | |

All thresholds are hashed into `config_hash`, so changing one triggers a fresh run rather than silently mutating history.

---

## 15. Test Plan

**Unit (synthetic audio)**
* 200 Hz sine, 3 s → `f0_median ≈ 200 ± 2 Hz`, `f0_std_st < 0.2`; 150→250 Hz linear chirp → positive slope, range ≈ 8.8 st.
* Two-speaker WAV: 120 Hz and 210 Hz alternating → per-speaker two-pass ranges do not cross-contaminate.
* Amplitude steps of 6 dB → `energy_dynamic_range ≈ 6 dB`; silence → `speech_ratio ≈ 0`, features `null`, not 0.
* Overlap frames excluded: add loud interferer during overlap → pitch stats unchanged vs. clean solo run (± 1 st).

**Unit (structured data)**
* Timeline with known intervals: `T_p`, `overlap_time`, transition gaps, and matrix match hand-computed values.
* Interruption cases: (a) B starts 0.2 s before A ends → `anticipatory_transition`; (b) B starts mid-A, A stops in 1 s → `interruption_candidate/yielded`; (c) B "yeah" over A → backchannel; (d) both start within 0.2 s → `simultaneous_start`.
* Pause detection: gap 0.29 s no, 0.31 s yes; gap between turns is **not** a pause.
* Filler: "um", "the the", "like" as verb (not counted), "it's like, a big change" (counted broad).
* Lexical: `mattr` invariant to doubling of text length (± 0.02); null for < 100 words.
* Linguistic: negation ("I don't agree" ⇒ disagreement, not agreement); "Let's go with option B" ⇒ proposal+decision; "Can you send the deck by Friday?" ⇒ question + action_item (owner=addressee, deadline=Friday).

**Property / robustness**
* Shuffling segment order does not change output. Adding an empty speaker does not change others. Single-speaker meeting ⇒ no transitions, latency `null`. Same-speaker overlapping segments merged. Unmapped speaker handled. Negative durations dropped.

**Integration / golden**
* Small recorded 3-minute, 3-speaker fixture with hand-labelled turns: assert turns count, `speaking_share` within ± 2 %, transitions matrix exact.
* Idempotency: run twice → identical rows; changed config → new `config_hash`.
* LLM validator: feed adversarial output ("he sounded nervous") → rejected.

**Quality metrics to track (ops):** ASR word-timestamp coverage %, share of low-confidence mappings, prosody-null rate, run time per hour of audio.

---

## 16. Limitations & Ethics

* Diarization/timing errors propagate into overlap, interruption and latency features — always show confidence and `n`.
* Whisper normalises disfluencies and punctuation; fillers, questions (no `?`) and sentence lengths are under-estimated.
* Pitch tracking is unreliable on creaky voice, telephony-compressed audio, and cross-talk; loudness depends on mic gain and distance.
* Language: lexicons are English; add per-language lexicon files and gate by detected language (`faster-whisper` returns `language`); non-English ⇒ linguistic features `null` unless a lexicon exists.
* Cultural, gender, dialect and neurodiversity differences influence turn-taking, pause length and prosody; the system reports **descriptions of behaviour**, not evaluations. Results must not be used as the sole basis for decisions about individuals. Participant consent and retention limits follow the platform policy (`04_API_AUTH` / privacy docs).

---

## 17. Implementation Roadmap (vertical slices)

1. **Slice A – Timing & turns** (no audio DSP): cleaning, activity grid, turns, backchannels, S01–S06, S18–S22, events, DB tables, `/summary`, `TalkTimeBar` + `SpeakerTimeline` + transition matrix.
2. **Slice B – Words & lexical:** pauses, WPM/rates, fillers, sentences, MATTR, questions (S07–S17).
3. **Slice C – Linguistic acts:** VADER, lexicons, dialogue acts, decisions/actions, `LinguisticTimeline`.
4. **Slice D – Prosody:** parselmouth pipeline, histograms, contours, energy, rhythm (P23–P35), `ProsodyPanel`, prosody quality.
5. **Slice E – Derived + LLM:** D01–D14, LLM payload, validator, report card, PDF section via `reportlab`.
6. **Slice F – Hardening:** windows/time series, config hashing, golden tests, performance pass, docs glossary.
