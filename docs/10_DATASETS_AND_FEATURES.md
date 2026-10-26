# 10 — Datasets and Features

## 0. How to read this document

Four layers must never be conflated. Every section below is written so it is clear which layer it belongs to:

| Layer | Question it answers | Where it lives |
|---|---|---|
| **DATASET PURPOSE** | Why was this corpus collected, and what does it actually contain? | Section 1–6 |
| **MODEL SUPERVISION** | Which labels, from which datasets, can train which supervised component (and which cannot)? | Sections 3–6, 16, 17 |
| **FEATURE EXTRACTION** | What signals do we compute from raw video/audio, regardless of which dataset produced the media? | Sections 7–14, 21–24 |
| **FINAL NTS SCORING** | How do fused features (and, where available, supervision) combine into the project's own NTS score and archetype? | Sections 17, 24, 26 |

A dataset can supply media for feature extraction without supplying labels for supervision, and it can supply labels for one dimension (e.g. leadership) while being irrelevant for another (e.g. personality). **No dataset is assumed to provide labels it was not actually annotated for.** Where a target label does not exist in a dataset, this is stated explicitly rather than implied or worked around silently.

---

## SECTION 1 — Dataset comparison table

| | **AMI Meeting Corpus** | **MPIIGroupInteraction** | **ELEA** | **NoXi** | **First Impressions V2** |
|---|---|---|---|---|---|
| **Purpose** | General-purpose multi-party meeting corpus (scenario-driven design-team meetings + some naturally occurring meetings), built to support meeting browsing/analysis research. | Small-group discussion corpus built to study group phenomena: rapport, eye contact, next-speaker prediction, emergent leadership, body language, engagement. | Corpus built specifically to study **emergent leadership** in newly formed small groups performing a "winter survival" consensus task. | Dyadic, screen-mediated **novice–expert knowledge-exchange** corpus built to study adaptive behavior, engagement, and interaction dynamics (incl. reactions to unexpected events). | Corpus built for **apparent personality** ("first impression") recognition from short single-person clips, plus an "invite to interview" label. |
| **Modality** | Audio + video + transcript + multi-level annotation. | Audio + video (8 synchronized cameras) + post-hoc annotation. | Audio + video + transcript + questionnaire-based annotation. | Audio + video (25fps) + Kinect 2.0 motion capture + annotation. | Video (with embedded audio) + ASR transcript + crowd-sourced trait scores. |
| **Video** | Yes — individual and room-view cameras. | Yes — 8 frame-synchronized cameras per session. | Yes — small-group video, portable multi-camera/Microcone setup. | Yes — dyadic, screen-mediated, 25fps + Kinect skeletal data. | Yes — ~15-second single-person clips, in-the-wild (YouTube-sourced). |
| **Audio** | Yes — close-talking and far-field microphones, per-speaker. | Yes — 4 microphones per session. | Yes — Microcone (commercial small-group mic array). | Yes — synchronized with video. | Yes — embedded in clip; used for ASR transcript only. |
| **Transcript** | Yes — high-quality manual orthographic transcription with word-level forced-alignment timing. | Not part of the core public release used here (annotation focus is behavioral, not linguistic). | Yes — manual transcriptions (English). | Partial — used in some derivative annotation efforts, not a core deliverable for our purposes. | Yes — ASR-generated (via Rev), not manually verified. |
| **Annotations present** | Dialogue acts, topic segmentation, extractive/abstractive summaries, named entities, head/hand gesture and gaze-direction tags, some emotional-state tags. **No formal leadership or engagement scale, no personality labels.** | Post-hoc perceived leadership / competence / dominance / liking / rapport ratings (self- and peer-rated); separately, dense body-language annotation (ECSI-derived, 14–15 classes); eye-contact annotations (every ~15s or via 10s context windows); fine-grained speaking-turn annotations (incl. overlapping speech, excluding backchannels); backchannel annotations; and (via later challenge extensions) frame-level continuous engagement annotations on a validation/test subset. **No personality trait labels.** | Self-reported and peer-reported personality (via questionnaire), leadership-related concepts, a self-reported dominance ranking (RDom), external-observer leadership/dominance ratings, and task-performance annotations for the winter survival task. **No frame-level body-pose/gaze/engagement annotation comparable to MPIIGroupInteraction; no formal dialogue-act/topic annotation like AMI.** | Continuous frame-level engagement annotation (0–1, multiple annotators), discrete body-property tags (e.g. "arms open", "energy head"), functional descriptors (turn-taking, some dialogue-act-like tags), interaction descriptors (interest, fluidity). **No leadership or personality labels.** | Crowd-sourced Big Five (OCEAN) trait scores per clip (continuous, 0–1, derived from pairwise comparisons + BTL model), an "invite to interview" binary/continuous label, perceived gender/ethnicity attributes. **No meeting context, no interaction/turn/leadership/engagement labels — single-person clips only.** |
| **Interaction labels** | Indirect only (dialogue acts / topic segments can be post-processed into turn-taking structure). | Yes — explicit, purpose-built (speaking turns, eye contact, next-speaker, backchannels). | Limited — audio/video available for deriving speaking-turn/visual-attention features, but no dedicated fine-grained interaction-label set comparable to MPIIGroupInteraction. | Yes — turn-taking and interaction-fluidity descriptors. | No — single-person clips, no interaction to label. |
| **Leadership labels** | **None.** | Peer/self-rated **perceived** leadership exists but was collected as a general social-rating questionnaire, not as this project's primary leadership ground truth. | Yes — this is the corpus's defining purpose: leadership-related self/peer ratings, external-observer leadership and dominance ratings. | **None.** | **None** (personality is not leadership; do not conflate). |
| **Engagement labels** | **None** (no formal engagement scale). | Yes, but only on a validation/test subset added for challenge purposes (not the full 22-session base corpus). | **None** in the sense of a continuous engagement scale (some questionnaire items are adjacent but not equivalent). | Yes — the corpus's core continuous annotation target. | **None.** |
| **Personality labels** | **None.** | **None.** | Yes — self- and peer-reported personality via questionnaire (not Big-Five-frame-level, but personality-adjacent). | **None.** | Yes — the corpus's defining purpose (Big Five / OCEAN). |
| **Access restrictions** | Publicly available for research use, standard AMI corpus license (attribution required); large download. | Restricted — request-based access via the dataset owners / MultiMediate challenge organizers; used historically under academic data-sharing agreements. | Restricted — hosted on Zenodo/Idiap as a "restricted" dataset; requires request/approval from Idiap. | Available via request through the NoXi/MultiMediate consortium; multilingual subsets vary in availability. | Publicly available for research (ChaLearn LAP release), standard research-use license; note ethical sensitivity of personality/interview labels on real identifiable people. |
| **Intended use in this project** | **Primary meeting dataset.** Backbone for pose/gaze/face/gesture/speech feature-extraction development and for interaction-density/turn-balance/dominance feature validation (Section 2). Not a source of leadership, engagement, or personality supervision. | **Feature validation + auxiliary supervision.** Primary use: validating body-behavior, eye-contact, and speaking-turn feature extraction against ground truth; secondary, opt-in use: engagement supervision (validation/test subset only) and *cautious*, clearly-labeled cross-reference for leadership-adjacent ratings — never treated as the leadership ground truth (Section 3). | **Leadership supervision.** The only dataset in this project treated as ground truth for a leadership-related supervised head (Section 4). Not used for meeting-scale interaction features (too small / different task) beyond what supports leadership modeling. | **Engagement/interaction auxiliary training data.** Used for gesture, facial-behavior, turn-taking, and engagement feature-model training/validation (Section 5). Not a meeting corpus (dyadic only) — not used for meeting-level interaction density. | **Auxiliary personality-representation dataset only.** Used to pretrain/validate facial and audio feature encoders on personality-adjacent signal; **never** used to directly supervise leadership, engagement, or meeting-level NTS output (Section 6). |

---

## SECTION 2 — AMI (primary meeting dataset)

AMI is used as the **primary source of meeting-realistic video and audio** for building and validating the full feature-extraction pipeline, because it is the only corpus in this set that is (a) multi-party, (b) meeting-scale in duration, and (c) has enough annotation richness (dialogue acts, topic structure, gesture/gaze tags) to sanity-check derived features, even though it does not supply leadership/engagement/personality ground truth itself.

### VIDEO features to extract (via the Human-based CV pipeline, Section 7)
- Person detections
- Person tracking (stable per-participant IDs across frames)
- Body pose
- Body keypoints
- Head orientation
- Face landmarks
- Iris / gaze
- Emotion probabilities
- Hand landmarks
- Gesture indicators
- Movement magnitude
- Movement frequency

### AUDIO features to extract (via STT/diarization adapters)
- Speech segments
- Speaker IDs
- Speaking duration
- Turn count
- Turn duration
- Response latency
- Interruptions
- Overlapping speech
- Participation ratio

### MEETING-level derived features
- Total participation
- Turn balance
- Speaker dominance
- Response patterns
- Interaction density

**Supervision note:** none of the above are supervised by AMI labels directly — they are unsupervised/rule-derived signal-processing features computed from AMI's raw audio/video. Where AMI's own dialogue-act and gesture/gaze annotations exist, they are used only to **validate** that derived features behave sensibly (e.g. does a detected turn boundary align with a dialogue-act boundary?), not to train a leadership/engagement/personality model — AMI does not provide those labels.

---

## SECTION 3 — MPIIGroupInteraction

### Intended use
- Body behavior (14–15 ECSI-derived body-language classes)
- Eye contact (per-participant, periodic or windowed annotation)
- Speaking turns (fine-grained, including overlap, excluding backchannels)
- Engagement (available only on a later-annotated validation/test subset, not the full base corpus)
- General interaction behavior (backchannels, next-speaker structure)

### How these labels are used
- **Feature validation:** the eye-contact and speaking-turn annotations are close to frame-accurate ground truth for exactly the kind of gaze/turn features this project computes from Human/audio adapters (Section 11, Section 10). MPIIGroupInteraction is the primary place to check precision/recall of the project's own gaze-ratio and turn-detection logic.
- **Supervised feature models:** the body-language class labels and eye-contact labels can directly supervise small, targeted classifiers/regressors (e.g. "is this participant currently making eye contact with participant X" or "which ECSI behavior class is this movement"), which then feed into the broader pose/gaze feature set as higher-confidence derived features rather than raw heuristics.
- **Evaluation:** the engagement subset (where available) can be used as a held-out evaluation signal for the project's own engagement-feature quality, but only as an auxiliary check — it is a small, challenge-specific annotation subset, not the primary engagement training source (that role belongs jointly to NoXi and this subset together, Section 5).

### Explicit leadership caveat
MPIIGroupInteraction does contain post-discussion perceived-leadership / dominance / competence / liking ratings, because the corpus has also been used for emergent-leadership research in the literature. **This project does not treat those ratings as its leadership supervision signal.** Reasons:
1. ELEA was purpose-built around leadership as its central research question, with a task (winter survival) explicitly designed to elicit emergent leadership; MPIIGroupInteraction's discussions were designed around eye-contact/turn-taking/rapport research questions, with leadership ratings collected as one of several general social-perception items.
2. Using both datasets' leadership-adjacent labels as if they were the same construct, collected under the same protocol, would silently merge two different measurement instruments. If a future iteration wants to use MPIIGroupInteraction's leadership ratings as **additional, secondary** supervision (e.g. multi-dataset training with a per-dataset label-space, Section 16), that must be an explicit, documented decision — not a default.

---

## SECTION 4 — ELEA

### Intended use
- Emergent leadership (the corpus's defining purpose)
- Leadership-related supervision (self-reported, peer-reported, and external-observer ratings)
- Dominance where available (self-reported dominance ranking, RDom; external-observer dominance ratings)
- Group interaction (small-group audio/video from the winter survival task, usable for deriving speaking-turn/visual-attention features that the original ELEA research itself used)

### Exactly how ELEA supervises the leadership component
- ELEA provides, per participant per group: a **self-reported dominance ranking**, **external-observer leadership and dominance ratings** (two observers per meeting, one male one female, each answering the same eight-question instrument), and **self/peer-reported personality**. These are participant-level, meeting-scoped labels — not frame-level.
- The leadership supervision path is therefore: engineered per-participant features (speaking-time share, turns held, visual-attention-received measures, and any others found predictive in the ELEA research literature) aggregated at the **meeting level**, regressed or ranked against the external-observer leadership rating (preferred, since it is less confounded by self-perception bias than the self-report) or the dominance ranking, using a participant-level train/validation/test split (Section 18) so that no participant's data leaks across splits.
- Because ELEA is small (approx. 10 hours, small-group compositions of 3–4/up to 6), the leadership model trained on it should be treated as a **narrow, specialized supervised head**, not a general-purpose leadership detector — its outputs feed into NTS scoring as one signal among several, with documented uncertainty (Section 25), not as a definitive leadership verdict.

### Explicit caveat
Leadership ratings in ELEA are about **emergent** leadership specifically — leadership that arises through interaction rather than formal authority. Nothing in ELEA licenses the claim that every visual/audio feature correlated with its leadership label is itself a general "leadership signal" outside the winter-survival-task context; the published ELEA research itself found that emergent leadership is **related but not equivalent** to dominance, and that simple audio features often outperformed more elaborate multimodal ones for this specific task. This project's use of ELEA-derived supervision should be read with that same caution rather than treated as an objectively established causal chain from any single visual/audio cue to "leadership."

---

## SECTION 5 — NoXi

### Intended use
- Gestures (low-level social signals, incl. body properties)
- Smiles / facial behavior
- Turn-taking (functional descriptors)
- Engagement (its core annotated construct — continuous, frame-level, 0–1, multiple annotators)
- Interaction fluidity (interaction descriptors: engagement, interest, fluidity)
- Conversational behavior more broadly (adaptive behavior around unexpected events, e.g. interruptions)

### Role in this project
NoXi is used as **auxiliary interaction/engagement training data** — specifically to train/validate the engagement-feature and facial/gesture-behavior models that later feed the fused feature set. It is not a meeting corpus (it is dyadic, screen-mediated, novice–expert), so it is **not** used to derive meeting-level interaction-density or turn-balance features across more than two participants, and it is not used for leadership or personality supervision (it carries neither label type).

Because NoXi's engagement annotation is the most direct, purpose-built, continuously-labeled engagement signal across all five datasets, it is the primary engagement-supervision dataset, with MPIIGroupInteraction's smaller engagement-annotated subset used as a secondary, out-of-domain validation/generalization check (as it has been used in prior engagement-estimation challenge work).

---

## SECTION 6 — First Impressions V2

### Use: auxiliary only

First Impressions V2 is used **only** as an auxiliary dataset for representation learning, never as a source of meeting-level, leadership, or engagement supervision.

- **Personality-related representation:** its ~10K short clips with crowd-sourced Big Five (OCEAN) trait scores make it useful for pretraining or validating facial/audio encoders that learn generally-useful "how a person presents" representations (expression dynamics, vocal delivery cues), which can be reused as feature-extraction backbones elsewhere in the pipeline.
- **Facial/audio feature learning:** the dataset's scale (~10K clips from 3K+ source videos) is useful for learning robust low-level facial-expression and short-clip audio-delivery features, which is a different task from meeting-level interaction modeling.
- **Why it is not a meeting-level dataset:** each clip is a single person speaking to a camera for ~15 seconds, with no other participants, no turn-taking, no group context. There is nothing in it to derive interaction, turn-balance, or leadership features from.
- **Why it should not directly determine leadership:** apparent personality (Big Five, as perceived by crowd annotators from a short clip) is a different construct from emergent or perceived leadership in a group context, and the dataset was never annotated for leadership. Any pipeline that let a First-Impressions-trained personality signal directly set or bias the NTS leadership component would be substituting a *correlated-but-distinct* construct for a label that was never collected — this project explicitly avoids that substitution. If personality-derived features are used anywhere downstream (e.g. as one input among many into fusion), that must be documented as a proxy/auxiliary signal, not as leadership ground truth (Section 25).

---

## SECTION 7 — Human feature extraction

All CV feature extraction in this project is performed through **[`vladmandic/human`](https://github.com/vladmandic/human)**, a TypeScript/TensorFlow.js library. Before implementation, the actual installed version's API (method names, config keys, and result object shape) must be inspected directly — do not assume method names from memory or from this document.

Human supports image, video (`<video>` element, including local files, webcam streams, and HLS/DASH/WebRTC-fed media), and webcam input natively, and ships default models for:

| Capability | Default model (per the Human project) |
|---|---|
| Face detection | MediaPipe BlazeFace (Back variant) |
| Face mesh | MediaPipe FaceMesh |
| Iris analysis | MediaPipe Iris |
| Face description (embedding) | HSE FaceRes |
| Emotion detection | Oarriaga Emotion |
| Body pose | MoveNet Lightning (alternatives: MoveNet Thunder, MultiPose, PoseNet, BlazePose, EfficientPose) |
| Hand analysis | HandTrack & MediaPipe HandLandmarks |
| Body segmentation | Google Selfie |
| Gesture | Derived from face/body/hand landmark heuristics within Human |

The project uses these capabilities where appropriate:
- Face detection, face mesh, iris → gaze and head-orientation features
- Emotion → facial/emotion features
- Body pose → pose and movement features
- Hand analysis / gestures → gesture indicators and hand-motion features
- Head rotation → head-tilt/orientation features

**Verification requirement:** because Human's API surface (`human.detect()`, `human.result`, `human.next()`, event-based access, config object shape, and per-module toggles) can change between versions, implementation must confirm exact method/property names against the installed package version's TypeDoc/README before wiring the `HumanAdapter` (docs/09_FILE_STRUCTURE.md, Section 4), rather than assuming this document's description is byte-exact.

---

## SECTION 8 — Feature schema

Every feature in the system's feature store must be documented with the following fields. Fields are illustrated, not exhaustively enumerated for every feature — Sections 10–14 define the specific feature names; this section defines the **schema** they must conform to.

```
feature_name: string                # canonical name, snake_case
category: enum                      # pose | gaze | face | speech | interaction | meeting
source: enum                        # Human | STTAdapter | DiarizationAdapter | derived
type: enum                          # float | int | bool | categorical | vector
unit: string | null                 # e.g. degrees, seconds, ratio, probability, null if unitless
sampling_frequency: string          # e.g. per-frame, per-window(1s/5s/...), per-turn, per-meeting
aggregation: list[string]           # e.g. [mean, std, p95] — which aggregations are computed over which windows
description: string                 # plain-language definition
limitations: string                 # known failure modes / assumptions
```

### Example

```
feature_name: pose_head_tilt
category: pose
source: Human
type: float
unit: degrees
sampling_frequency: per-frame, aggregated per-window
aggregation: [mean, std, p95]
description: Angular tilt of the head relative to the vertical camera axis.
limitations: camera angle dependent; unreliable when face is not detected;
             not corrected for seated-camera-height variation across recordings.
```

Every feature defined in Sections 10–14 must be entered into a machine-readable feature registry (e.g. `configs/feature_schema.yaml`, per docs/09_FILE_STRUCTURE.md) following exactly this schema before it is used anywhere downstream.

---

## SECTION 9 — Temporal features

For every participant, features are computed over rolling/fixed windows:

- 1 second
- 5 seconds
- 10 seconds
- 30 seconds
- 60 seconds
- meeting-level (the entire session)

For each applicable base feature (Sections 11–14), the following aggregations are computed per window, where meaningful for that feature's type:

| Aggregation | Applies to |
|---|---|
| mean | continuous features |
| std | continuous features |
| min | continuous features |
| max | continuous features |
| median | continuous features |
| percentiles (e.g. p25/p75/p95) | continuous features |
| trend (slope over the window) | continuous features with enough samples per window |
| frequency (events per unit time) | discrete/event features (e.g. gaze switches, interruptions) |
| duration | state features (e.g. time spent in a pose state) |
| ratio | features naturally expressed as a proportion (e.g. speaking ratio, gaze-on-camera ratio) |

Not every aggregation applies to every feature — e.g. "trend" is not meaningful for a boolean state feature, and this must be reflected in each feature's schema entry (Section 8) rather than computed uniformly and discarded silently.

---

## SECTION 10 — Speaking features

| Feature | Definition |
|---|---|
| `total_speaking_time` | Sum of speech-segment durations attributed to the participant within the window. |
| `speaking_ratio` | `total_speaking_time` / window duration. |
| `turn_count` | Number of distinct speaking turns started by the participant in the window. |
| `mean_turn_duration` | Mean duration of the participant's turns in the window. |
| `median_turn_duration` | Median duration of the participant's turns in the window. |
| `max_turn_duration` | Longest single turn duration in the window. |
| `response_latency` | Mean time between the end of another participant's turn and the start of this participant's next turn (when this participant is the next speaker). |
| `interruption_count` | Count of turns where this participant began speaking while another participant's turn was still active (per Section 10's overlap definition, not counting backchannels). |
| `overlap_ratio` | Total time this participant's speech overlaps with any other participant's speech, divided by this participant's `total_speaking_time`. |
| `turn_switch_rate` | Number of speaker changes per unit time within the window (meeting-level feature, not per-participant, or computed per-participant as "switches following this participant"). |
| `participation_entropy` | Shannon entropy of the speaking-time distribution across all participants in the window (meeting-level feature) — low entropy indicates one or few participants dominate. |

---

## SECTION 11 — Gaze features

| Feature | Definition |
|---|---|
| `camera_gaze_ratio` | Proportion of window time the participant's estimated gaze direction falls within a camera-facing cone. |
| `left_gaze_ratio` | Proportion of window time gaze is directed left of the camera-facing cone (relative to the participant's own frame). |
| `right_gaze_ratio` | Proportion of window time gaze is directed right of the camera-facing cone. |
| `downward_gaze_ratio` | Proportion of window time gaze is directed downward (e.g. toward notes/device). |
| `gaze_switch_rate` | Number of discrete gaze-direction-class changes per unit time. |
| `gaze_stability` | Inverse-variance style measure of how steady gaze direction is within the window (higher = more stable/fixated). |
| `head_orientation_variance` | Variance of head-orientation angle within the window (complements gaze; head orientation and eye gaze are related but not identical). |

**Caution (explicit, per project requirement):** "gaze direction" here is always relative to the specific camera/meeting geometry of a given recording — a fixed webcam versus a room-view meeting camera versus a screen-mediated dyadic setup (as in NoXi) each define a different meaning for "gaze toward camera" versus "gaze toward another participant." Gaze features are not comparable across datasets or deployments without first normalizing for camera position and, in multi-camera meeting rooms, for which participant is being looked at (participant-to-participant gaze, Section 14) versus simple camera-facing gaze.

---

## SECTION 12 — Pose features

| Feature | Definition |
|---|---|
| `head_tilt` | Angular tilt of the head relative to vertical (see Section 8 example). |
| `torso_lean` | Forward/backward and lateral lean angle of the torso relative to a neutral seated posture. |
| `shoulder_orientation` | Rotation of the shoulder line relative to the camera plane. |
| `body_motion_energy` | Aggregate magnitude of body-keypoint displacement per unit time. |
| `hand_motion_energy` | Aggregate magnitude of hand-keypoint displacement per unit time. |
| `posture_stability` | Inverse-variance measure of torso/shoulder position over the window (higher = steadier posture). |
| `movement_frequency` | Count of distinct movement events (motion-energy peaks above a threshold) per unit time. |

---

## SECTION 13 — Facial features

Emotion probabilities and facial movement are used **as behavioral signal, not as psychological diagnosis.**

| Feature | Definition |
|---|---|
| `smile_probability` | Model-estimated probability of a smile expression at a given frame/window. |
| `neutral_probability` | Model-estimated probability of a neutral expression. |
| `emotion_distribution` | Full probability vector across the model's emotion classes (as returned by Human's emotion model), not a single collapsed label. |
| `facial_activity` | Aggregate magnitude of facial-landmark movement per unit time (a proxy for expressiveness, not for any specific emotion). |
| `expression_change_rate` | Number of discrete expression-class changes per unit time. |

**Explicit constraint:** these are model-estimated probabilities from a general-purpose emotion classifier, subject to the same lighting/camera-angle/cultural-expression caveats as any facial-expression model. They must never be converted into definitive psychological conclusions (e.g. "this participant is anxious," "this participant is disengaged") either in the feature layer or in any user-facing report copy — downstream consumers should treat `emotion_distribution`/`smile_probability` as one weak, noisy signal among many contributing to fused features, not as a diagnosis.

---

## SECTION 14 — Interaction features

| Feature | Definition |
|---|---|
| Speaking dominance | A participant's share of total meeting speaking time relative to an equal-share baseline (derived from Section 10 features). |
| Turn balance | Meeting-level evenness of turn distribution across participants (e.g. via `participation_entropy`, Section 10). |
| Response behavior | Aggregated `response_latency` and next-speaker patterns (who tends to speak after whom). |
| Overlap | Meeting-level aggregate of `overlap_ratio`/`interruption_count` across all participants. |
| Interaction density | Rate of speaker changes plus gesture/gaze events per unit time — a general "how much is happening" signal. |
| Participant-to-participant gaze | Where technically possible (i.e. where camera geometry and multi-participant framing allow estimating *which* participant is being looked at, not just "gaze toward camera") — proportion of time participant A's gaze target is estimated to be participant B. Requires multi-camera or wide-frame setups (as in AMI's room-view cameras or MPIIGroupInteraction's 8-camera rig); not computable from a single-participant webcam framing. |
| Group participation | Proportion of participants who speak/gesture at least once within a given window — a coarse "is everyone engaged" signal at the meeting level. |

---

## SECTION 15 — Feature normalization

Three normalization scopes are defined, and they are not interchangeable:

- **Per-person normalization:** a participant's features are normalized against that same participant's own baseline (e.g. z-scored against their own meeting-long mean/std), useful for detecting *change* in that individual's behavior over time within a session.
- **Per-meeting normalization:** features are normalized against the distribution of all participants within the same meeting, useful for relative comparisons ("who spoke more than average in this meeting").
- **Dataset normalization:** features are normalized against the distribution observed across an entire training dataset (e.g. all of AMI), useful for making a supervised model's inputs comparable across many different meetings/recording setups.

**Leakage avoidance:** normalization statistics (means/stds/percentile boundaries) must be computed only from the training split (Section 18) when normalization feeds a supervised model — never from validation/test data, and never from a statistic that spans a single meeting when the model is meant to generalize across meetings. Per-meeting normalization is by definition meeting-scoped and does not leak across meetings, but if it is used as an input to a cross-meeting supervised model, that model must still be trained/evaluated with meeting-level and participant-level splits so it does not learn meeting-specific normalization artifacts as if they were general signal.

---

## SECTION 16 — Dataset harmonization

Different datasets do not share an annotation scheme, and the pipeline must not force one dataset's label space onto another's. Harmonization instead happens at the **feature** layer, which is dataset-agnostic, while each dataset's own label space is kept separate for whatever supervision it can legitimately provide:

```
COMMON FEATURE SPACE
   (Sections 8–14: pose/gaze/face/speech/interaction features,
    computed identically regardless of source dataset)
        ↓
DATASET-SPECIFIC LABEL SPACE
   (AMI: dialogue acts, topic segments — no leadership/engagement/personality
    MPIIGroupInteraction: eye contact, speaking turns, body-language classes,
        engagement (subset only), leadership-adjacent ratings (secondary only)
    ELEA: leadership/dominance ratings, personality (questionnaire)
    NoXi: engagement, gesture/facial-behavior descriptors
    First Impressions V2: Big Five personality, interview label)
        ↓
MODEL-SPECIFIC SUPERVISION
   (Each supervised head is trained only against the label space
    that dataset actually provides for that head — e.g. the leadership
    head trains against ELEA's leadership labels, optionally with
    MPIIGroupInteraction's leadership-adjacent ratings as a clearly
    flagged secondary source; the engagement head trains against
    NoXi + MPIIGroupInteraction's engagement subset; the personality-
    adjacent representation trains against First Impressions V2 only
    and is never used as leadership/engagement ground truth.)
```

This three-layer structure means a new dataset can be added by (a) mapping its raw media into the common feature space via the same Human/audio adapters, and (b) declaring, explicitly, which of its labels (if any) may supervise which model-specific head — without ever assuming symmetry between datasets that were not designed to be comparable.

---

## SECTION 17 — Training strategy

| Stage | Description |
|---|---|
| **Stage 1 — Pretrained CV models** | Use Human's pretrained face/body/hand/emotion models as-is (no retraining) as the base perception layer. |
| **Stage 2 — Feature extraction** | Run the common feature-extraction pipeline (Sections 8–14) over AMI (primary), plus MPIIGroupInteraction, ELEA, NoXi, and First Impressions V2 media, producing the common feature space. |
| **Stage 3 — Dataset-specific supervised models** | Train small, targeted supervised heads only where a dataset actually provides the relevant label: eye-contact/speaking-turn/body-language classifiers on MPIIGroupInteraction; a leadership/dominance head on ELEA (optionally + MPIIGroupInteraction as secondary); an engagement head on NoXi + the MPIIGroupInteraction engagement subset; a personality-adjacent representation encoder on First Impressions V2. |
| **Stage 4 — Feature fusion** | Combine common features with the outputs of Stage 3's supervised heads (where available) into a unified per-participant feature vector (Section 23–24). |
| **Stage 5 — NTS scoring** | Train/apply the project's own NTS scoring model over the fused feature vector — this is the project's own model, not any one dataset's label, and it is where proxy/engineered scores (Section 25) must be most carefully documented. |
| **Stage 6 — Calibration** | Calibrate NTS score outputs (e.g. isotonic regression / temperature scaling on a held-out set) so scores are comparable across meetings and over time, rather than raw uncalibrated model outputs. |
| **Stage 7 — Evaluation** | Evaluate each stage's outputs against the metrics defined in Section 19, using the splitting discipline in Section 18. |

---

## SECTION 18 — Train/validation/test splits

- **Participant-level splitting:** a given participant's data must appear in only one of train/validation/test, across all sessions/recordings they appear in (relevant for datasets like AMI/MPIIGroupInteraction/ELEA/NoXi where the same person can appear in multiple recordings).
- **No participant leakage:** enforced by splitting on participant ID (or, where participant identity is not tracked across sessions, on a conservative proxy such as recording+role) before any feature/label extraction, not after.
- **Meeting-level isolation:** for meeting/session-scoped datasets, an entire meeting/session must be wholly in one split — never split within a single meeting's timeline, since that would let a model see near-adjacent context from the "future" of a meeting it is being tested on.
- **Dataset-level validation where appropriate:** in addition to within-dataset splits, out-of-dataset validation is used where the target task allows it (e.g. validating an engagement model trained on NoXi against the MPIIGroupInteraction engagement subset, as prior published work in this space has done) to check generalization rather than relying solely on within-dataset held-out performance.

---

## SECTION 19 — Evaluation

| Task | Metric(s) |
|---|---|
| Pose | Tracking stability (e.g. keypoint-track continuity / ID-switch rate over a session) — no accuracy claim is made without ground-truth pose annotation, which none of these datasets provide at scale. |
| Gaze | Classification/regression metrics (e.g. accuracy/F1 for discrete gaze-direction classes, or MAE for continuous gaze-angle estimates) — only where ground-truth labels exist, i.e. against MPIIGroupInteraction's eye-contact annotations. |
| Speaking turns | Precision / recall / F1 for turn-boundary and turn-attribution detection — validated against MPIIGroupInteraction's fine-grained speaking-turn annotations (and AMI's dialogue-act-derived turn structure as a secondary check). |
| Engagement | F1 (if treated as a discrete class) or MAE (if treated as the continuous 0–1 NoXi-style target) depending on how the target is formulated for a given model version. |
| Leadership | F1 / MAE / RMSE depending on label formulation (classification of "is the emergent leader" vs. regression against a continuous dominance/leadership rating) — evaluated against ELEA's held-out participants/meetings. |
| Final NTS | Calibration diagnostics (e.g. reliability curves) plus MAE / RMSE / F1 as appropriate to however the NTS output is formulated (continuous score vs. categorical archetype). |

**No expected accuracy figures are stated in this document.** Actual achievable performance depends on final model choices, data volume after applying the splitting rules above, and feature quality, and must be measured empirically rather than assumed in advance.

---

## SECTION 20 — Feature provenance

Every feature record persisted anywhere in the system (training-time or inference-time) must carry:

```
source_dataset: string        # e.g. "AMI", "live_session", "uploaded_file"
source_media: string          # storage URI / recording identifier
participant_id: string
timestamp: string             # frame time or window start/end
feature_version: string       # schema/version identifier, ties to configs/feature_schema.yaml
extraction_model: string      # e.g. "Human@<version>:body-movenet-lightning"
confidence: float | null      # model confidence where available; null if not applicable
quality_flag: enum            # e.g. ok | degraded | dropped_frames | low_confidence | out_of_frame
```

This matches the provenance requirement in `docs/08_ORCHESTRATOR.md` (Section 12, dropped-frame/backpressure quality flagging) — the orchestrator's `quality_flag` annotations for degraded live-session windows are the same field referenced here, not a separate concept.

---

## SECTION 21 — Simultaneous use of both GitHub repositories

The two reference repositories serve **strictly separate responsibilities** and are never merged:

| Repository | Responsibility |
|---|---|
| **[`vladmandic/human`](https://github.com/vladmandic/human)** | **CV feature extraction.** A client/server JS/TS library that takes an already-available image/video/webcam/WebRTC input and produces face/body/hand/emotion/gaze detections. It knows nothing about meetings, bots, or platform connectivity. |
| **[`Umer-2612/realtime-meeting-intelligence`](https://github.com/Umer-2612/realtime-meeting-intelligence)** | **Meeting media ingestion / streaming architecture reference.** Its actual repository structure is a Teams bot (Windows, .NET, Microsoft Graph + Microsoft.Psi), a Zoom bot (C++, Zoom Meeting SDK, raw audio/video capture and publishing), and a Python stream-processor that consumes the fan-out from either bot for analytics. It knows nothing about facial/body computer vision models — it is only responsible for getting a normalized audio/video stream *out of* a live Zoom/Teams meeting. |

This project treats the second repository as an **architectural reference and integration target**, not a library imported directly into the backend — the actual production `MeetingPlatformAdapter` (docs/09_FILE_STRUCTURE.md, Section 4) may reuse patterns from it (bot lifecycle management, raw media subscription) but produces output in this project's own normalized `MediaSource` event format (Section 22), which is then handed to the same Human/audio adapters used for file and webcam modes.

### Mode-specific flow

**FILE MODE**
```
video file → OpenCV/FFmpeg (decode/frame-extract) → Human (CV inference) → features
```

**LIVE CAMERA**
```
browser camera → Human (CV inference, in-browser or via WebSocket to a server-side Human instance) → realtime feature stream
```

**MEETING MODE**
```
Zoom/Teams → meeting media ingestion architecture (Teams bot / Zoom bot / stream-processor,
             modeled on realtime-meeting-intelligence) → normalized media stream
             → Human / audio processors → features
```

In every mode, once media reaches the "Human / audio processors" step, the feature-extraction contract (Sections 8–14) is identical — only how the raw media arrived differs.

---

## SECTION 22 — Unified internal media interface

```
MediaSource (abstract)
├── FileMediaSource        # local/uploaded video file, decoded via OpenCV/FFmpeg
├── WebcamMediaSource      # live browser camera / WebRTC track
├── ZoomMediaSource        # normalized stream from the Zoom-bot side of the ingestion architecture
└── TeamsMediaSource       # normalized stream from the Teams-bot side of the ingestion architecture
```

All four implementations emit the same normalized stream/event format downstream (frame batches + audio chunks + basic session metadata such as participant roster where known), so that `EXTRACTING_VIDEO`/`EXTRACTING_AUDIO` (docs/08_ORCHESTRATOR.md) and the Human/audio adapters do not need to know which `MediaSource` implementation produced their input. `ZoomMediaSource` and `TeamsMediaSource` are explicitly placeholders for **future** work (per the project's phasing) — their existence in the interface does not imply they are implemented in the MVP (Section 26/27).

---

## SECTION 23 — Unified feature interface

```
FrameFeatures        # single-frame, single-participant CV output (pose, gaze, face, hand landmarks + derived indicators)
AudioFeatures         # single-segment audio output (speech/silence, speaker ID, prosodic/turn-relevant signal)
ParticipantFeatures   # windowed/meeting-level aggregation of FrameFeatures + AudioFeatures for one participant
                      # (Sections 9–14's feature set, at whatever window granularity is requested)
MeetingFeatures       # meeting-level aggregation across all ParticipantFeatures (turn balance, interaction
                      # density, group participation, etc. — Section 14's meeting-scoped features)
```

These four types are the contract every worker (docs/08_ORCHESTRATOR.md, `cv_worker`/`audio_worker`/`feature_worker`) and every dataset-ingestion script under `ml/preprocessing` (docs/09_FILE_STRUCTURE.md) must produce/consume — whether the underlying data came from AMI, a live session, or an uploaded file.

---

## SECTION 24 — Feature fusion

```
VIDEO FEATURES  (pose, gaze, face — Sections 11–13)
      +
AUDIO FEATURES  (speech/turn — Section 10)
      +
INTERACTION FEATURES  (Section 14, itself derived from the above two plus multi-participant context)
      ↓
PARTICIPANT FEATURE VECTOR   (a single ParticipantFeatures record, Section 23)
      ↓
NTS MODEL
```

The NTS model consumes the fused `ParticipantFeatureVector` (and, at the meeting level, `MeetingFeatures`) as its input; it does not consume raw video/audio, and it does not re-derive features itself — feature fusion is a distinct pipeline stage (`FUSING_FEATURES` in docs/08_ORCHESTRATOR.md) that completes before `SCORING` begins.

---

## SECTION 25 — Important scientific limitation

**The datasets used in this project do not provide direct supervision for every desired NTS dimension.** This is a structural fact about the available data, not a temporary gap to be silently engineered around. Concretely:

- **Directly supervisable today:** eye contact, speaking-turn structure, and (on a subset) engagement (via MPIIGroupInteraction); engagement more broadly (via NoXi); emergent leadership/dominance (via ELEA); apparent personality representation (via First Impressions V2, for representation learning only, not for NTS output directly).
- **Must use proxy labels:** any NTS dimension not directly covered by the above (e.g. broader "team contribution" or dimensions the project defines that don't map onto any single dataset's label) must be approximated via a documented combination of the directly-supervised signals, engineered features, or expert-defined heuristics — clearly marked as a proxy, with the proxy's construction recorded alongside the feature/label it approximates.
- **May initially use engineered scores:** where no dataset-derived supervision exists at all for a dimension, an initial engineered scoring function (e.g. a weighted combination of interaction/speaking/gaze features chosen by domain reasoning rather than learned from labels) may be used as a placeholder, but must be labeled as engineered/heuristic in all downstream metadata and reporting, never as "measured."
- **All such choices must be documented:** the feature/label registry (Section 8, `configs/feature_schema.yaml`) must record, for every NTS-facing signal, whether it is directly supervised, a proxy, or engineered, and from which dataset(s) if any.
- **Validation is required:** any proxy or engineered score must go through the evaluation process in Section 19 to the extent possible (e.g. correlating an engineered "contribution" score against available adjacent ground truth, human review of a sample) before being trusted in a report.

**A proxy score must never be presented to an end user, or documented internally, as an objectively measured truth.** Report copy and API documentation must reflect the actual epistemic status of each NTS dimension (measured vs. proxy vs. engineered).

---

## SECTION 26 — Recommended MVP features

The smallest feature set sufficient to demonstrate the project end-to-end:

| Category | MVP features |
|---|---|
| Pose | `torso_lean`, `head_tilt` (used here as "head orientation"), `body_motion_energy` (as "body motion") |
| Gaze | A single derived "gaze direction" class (camera / left / right / down, from Section 11's ratios) and `camera_gaze_ratio` as "attention ratio" |
| Face | `smile_probability` or the full `emotion_distribution` as "expression probability", `facial_activity` |
| Speech | `total_speaking_time`, `turn_count`, `response_latency` |
| Interaction | Turn balance (`participation_entropy` or a simpler share-based measure), `interruption_count` |

### Mapping to the first NTS model

These MVP features are combined, per participant, into a minimal `ParticipantFeatureVector` (Section 23) covering exactly the five categories above. The first NTS model is intentionally simple: an engineered or lightly-supervised scoring function (per Section 25's "engineered scores" category, since MVP scope does not include a fully trained leadership/engagement head) that combines these ten-ish signals into a small number of interpretable sub-scores (e.g. an engagement-leaning sub-score from gaze/face/pose, a participation-leaning sub-score from speech/interaction features), which are then surfaced as the first version of the NTS report — explicitly labeled as an early, engineered-score version pending the supervised-model work in Section 17's later stages.

---

## SECTION 27 — Future features (explicitly out of MVP scope)

Not implemented in MVP; recorded here so they are not lost or accidentally attempted early:

- Richer gesture recognition (beyond Human's built-in gesture heuristics)
- Interaction graphs (explicit participant-to-participant interaction network structure over a meeting)
- Cross-person gaze at scale (participant-to-participant gaze, Section 14, generalized beyond the specific multi-camera setups where it's currently feasible)
- Conversational embeddings (learned representations of dialogue content/structure, likely requiring the transcript modality more heavily than the MVP does)
- Advanced temporal transformers (sequence models over the windowed features in Section 9, replacing the simple aggregation-based MVP approach)
- Multimodal transformers (joint video+audio+text architectures for feature fusion, replacing the concatenation-style fusion in Section 24)

These are natural extensions once the MVP pipeline, dataset harmonization discipline (Section 16), and evaluation process (Section 19) are established and validated — attempting them before that foundation exists would make it harder to tell whether a result reflects real signal or an artifact of under-validated data handling.
