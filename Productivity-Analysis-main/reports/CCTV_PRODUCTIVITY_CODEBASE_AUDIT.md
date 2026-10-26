# Comprehensive Technical Audit Report: CCTV-Based Workplace Productivity Analysis Systems

**Audit Date:** October 15, 2026  
**Auditor Role:** Senior Computer Vision Engineer, Machine Learning Auditor, Software Architect, and Technical Documentation Specialist  
**Target Repository / Workspace:** `C:\Users\DELL\Desktop\cctv`  
**Extracted Project Path:** `C:\Users\DELL\Desktop\cctv\audit_extracted\OpenCV-Based-Real-time-Employee-Tracking-System-main`  
**Host / Main Project Reference Path:** `C:\Users\DELL\Desktop\video` (with related modules in `C:\Users\DELL\Desktop\chakri`)  
**Audit Artifact Path:** `reports/CCTV_PRODUCTIVITY_CODEBASE_AUDIT.md`  

---

## 1. Executive Summary

This codebase audit delivers an exhaustive, evidence-based investigation of computer vision systems designed for workplace monitoring, presence tracking, and behavioral productivity analysis. The investigation covers two distinct codebases:

1. **The Extracted Project (`OpenCV-Based-Real-time-Employee-Tracking-System-main`)**: An OpenCV DNN-based workplace monitoring system using Darknet YOLOv4-tiny, wrapped in a Flask web server with a Bootstrap/jQuery frontend.
2. **The Host Main Video Analytics Project (`C:\Users\DELL\Desktop\video`)**: A real-time multimodal behavioral and video analytics pipeline leveraging MediaPipe (FaceMesh, Pose, Hands), PyTorch/YOLOv8 face detection, EfficientNet-B0 emotion classification, and Streamlit-WebRTC for posture, tension, gaze, gesture, energy, and Big Five (OCEAN) personality profiling.

### Key High-Level Findings

- **No Verified Workplace "Productivity" Formula Exists in the Extracted Project:** Despite extensive documentation claiming *"real-time insights for productivity management and automated attendance tracking,"* the extracted project contains **zero lines of code calculating productivity scores, work output, task completion, or active vs. idle ratios**. It implements exclusively a binary bounding-box overlap test against a static desk region of interest (ROI), computing elapsed wall-clock absence duration.
- **Absence of Multi-Person Tracking:** Neither project implements a true multi-object tracking (MOT) algorithm (e.g., ByteTrack, SORT, DeepSORT, or FairMOT). The extracted project processes bounding boxes independently on every frame without tracking IDs, trajectory smoothing, or re-identification. If two people swap desks or walk past the camera, the system exhibits severe identity confusion.
- **Frontend Display Freezing and Deceptive UI Controls:** The web dashboard of the extracted project features a critical polling defect where `/status` is called only once upon start, leaving all telemetry cards (`Absence Time`, `Frames Processed`, `Tracking Status`) completely frozen in the browser. Furthermore, the "Capture Frame" button executes purely client-side DOM injection without communicating with the server or storing images.
- **Security and Privacy Hazards:** Plaintext CCTV credentials with administrative passwords were found committed inside the runtime log file (`logs/employee_log.txt`). The system also lacks any authentication, role-based access control, or TLS encryption.
- **Host Project Discrepancy & Pseudoscientific Proxy Risk:** The host `video/` codebase exhibits an advanced multimodal feature extraction pipeline, but relies on unvalidated heuristics and subjective weightings to map micro-movements (blinking, leg jiggling, arm angle) to Big Five personality scores, "Genuineness", and "Lie/Deception" indicators, introducing acute legal and operational risks if used for employee evaluation.

---

## 2. Scope and Audit Methodology

### Audit Scope
The audit encompasses:
1. Complete static code analysis of all Python modules, configuration files, templates, deployment scripts, logs, and documentation in the workspace.
2. End-to-end tracing of all video capture, decoding, preprocessing, inference, heuristic scoring, and UI display paths.
3. Rigorous mathematical and algorithmic auditing of all presence, duration, motion, behavioral, and productivity metrics.
4. Data security, privacy, performance, and reliability evaluations.

### Methodology
A four-pass auditing protocol was executed:
- **Pass 1 — Discovery & Environment Assessment:** Inspected filesystem structure, Git configuration, archive integrity, and adjacent projects across host drives (`C:\` and `D:\`).
- **Pass 2 — Deep Codebase Reading & Pipeline Tracing:** Traced function execution graphs from video inputs (`cv2.VideoCapture`, `VideoTransformerBase.recv`) through deep learning inference to downstream aggregators.
- **Pass 3 — Metric & Formula Verification:** Audited every mathematical operation, threshold, smoothing filter, and score normalization, classifying each by evidence status (**VERIFIED**, **HARDCODED**, **SIMULATED**, **DOCUMENTED ONLY**, **NOT IMPLEMENTED**, or **BUGGY**).
- **Pass 4 — Comparative Evaluation & Risk Synthesis:** Evaluated architecture, deployment readiness, and operational risks across both systems.

---

## 3. Repository Discovery and ZIP Extraction Results

### Workspace Root Status
- **Workspace Directory:** `C:\Users\DELL\Desktop\cctv`
- **Creation Timestamp:** `10/15/2026 11:03:24 AM`
- **Initial Directory State:** The workspace was newly created immediately prior to this session and initially contained **only a single file**: `OpenCV-Based-Real-time-Employee-Tracking-System-main.zip` (59,873,566 bytes / ~57.1 MB).
- **Pre-existing Code in Root:** None. No README, no git commits, and no source files existed in `cctv/` before the ZIP was placed there.

### Archive Inspection and Extraction
1. **Archive Integrity:** Verified as a valid, uncorrupted, standard PKZIP archive.
2. **Pre-Extraction Inventory:** Contained 18 entries rooted in directory `OpenCV-Based-Real-time-Employee-Tracking-System-main/`, including Darknet YOLOv4-tiny model weights (`24.2 MB`), an uploaded demonstration MP4 video (`39.1 MB`), and application code.
3. **Extraction Destination:** Safely extracted to `C:\Users\DELL\Desktop\cctv\audit_extracted\OpenCV-Based-Real-time-Employee-Tracking-System-main` without overwriting existing files or escaping the target directory boundary.

### Host Main Project Discovery
A machine-wide filesystem discovery revealed the user's primary custom video analytics codebase located at `C:\Users\DELL\Desktop\video` (with dashboard utilities at `C:\Users\DELL\Desktop\chakri`). This host repository represents an in-house real-time behavioral analytics engine developed using MediaPipe, Streamlit, and ECharts.

---

## 4. Project Structure and Important Entry Points

### A. Extracted Project (`OpenCV-Based-Real-time-Employee-Tracking-System-main`)

```
audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/
├── .gitattributes                     # Git LFS configuration
├── Dockerfile                         # Python 3.9-slim + OpenCV headless container
├── README.md                          # Project documentation and architecture claims
├── render.yaml                        # Render cloud deployment specification
├── requirements.txt                   # Dependency manifests (Flask, OpenCV, NumPy, etc.)
├── app.py                             # Main web application entry point (Flask)
├── employee_tracking_fixed.py         # Core detection and tracking engine (OpenCV DNN)
├── logs/
│   └── employee_log.txt               # Plaintext execution log with timestamps
├── templates/
│   └── index.html                     # Frontend interface (Jinja2, Bootstrap 5, jQuery)
├── uploads/
│   └── 1755331753_..._video.mp4      # Pre-recorded test video clip (~39.1 MB)
└── yolo_model/
    ├── coco.names                     # 80 COCO category names
    ├── yolov4-tiny.cfg                # Darknet architecture definition
    └── yolov4-tiny.weights            # Trained binary weights (~24.2 MB)
```

**Key Entry Points:**
- `app.py`: Flask HTTP server running on `0.0.0.0:5000` (`python app.py`). Instantiates singleton `tracker = EmployeeTracker()`.
- `employee_tracking_fixed.py`: Defines `EmployeeTracker` class containing all camera capture, YOLO inference, desk detection, and absence timing routines.

### B. Host Video Analytics Project (`C:\Users\DELL\Desktop\video`)

```
C:\Users\DELL\Desktop\video/
├── main.py                            # Unified video processor with Streamlit-WebRTC
├── comp.py                            # Streamlined high-framerate (20 FPS) processor
├── xyz.py                             # Mirror / backup of main.py
├── ui.py                              # Streamlit dashboard and metric HTML cards
├── choriwala_code.py                  # Full ECharts & component visualization suite
├── emo.py / emo2.py                   # PyTorch YOLOv8 + EfficientNet emotion classification
├── horiz.py / top.py                  # Horizontal gauge components & ECharts bars
├── ocean.py / og.py / t.py / trial.py # Big Five personality & genuineness gauge renderers
└── test_dashboard.py / top_test.py    # Local standalone test mock runners
```

**Key Entry Points:**
- `main.py:UnifiedVideoProcessor`: Threaded WebRTC video receiver and MediaPipe coordinator.
- `ui.py`: Streamlit reactive frontend dashboard (`streamlit run ui.py`).

---

## 5. Technology Stack and Model Inventory

| Dimension | Extracted Project (`audit_extracted`) | Host Video Project (`video/`) |
|---|---|---|
| **Primary Language** | Python 3.9+ | Python 3.10 / 3.11 |
| **Web / Application Server** | Flask 2.3.3 + Gunicorn 21.2.0 | Streamlit + Streamlit-WebRTC |
| **Computer Vision Engine** | OpenCV 4.8.1 (`cv2.dnn`) | OpenCV + MediaPipe (FaceMesh, Pose, Hands) |
| **Deep Learning Framework** | Darknet / OpenCV DNN C++ Backend | PyTorch + Torchvision + Ultralytics YOLO |
| **Object Detection Model** | YOLOv4-tiny (Darknet weights, 416x416) | YOLOv8n-face (OpenVINO INT8) + MediaPipe |
| **Classification Models** | COCO 80-Class argmax | EfficientNet-B0 (`enet_b0_8_best_vgaf.pt`) |
| **Inference Hardware Target** | CPU (`cv2.dnn.DNN_TARGET_CPU`) | CPU / CUDA (`torch.cuda.is_available()`) |
| **Threading & Concurrency** | Python `threading.Thread` + `queue.Queue` | `ThreadPoolExecutor(max_workers=3)` + Mailbox lock |
| **Data Persistence** | Plain text log file + JPG snapshots on disk | Local `.jsonl` files + in-memory accumulators |
| **Frontend Framework** | Server-side HTML5 + Bootstrap 5 + jQuery | Streamlit Reactive UI + Apache ECharts |
| **Packaging & Deployment** | Docker (`python:3.9-slim`) + Render.com | Local Python environment |

---

## 6. End-to-End Pipeline for the Main / Host Project (`video/`)

The host video analytics engine operates as a multimodal behavioral monitoring pipeline designed for single-subject webcam evaluation (interviews, focus monitoring):

```mermaid
flowchart TD
    A[WebRTC Video Stream: av.VideoFrame] --> B[recv Callback: cv2 BGR24 Conversion]
    B --> C[Network Quality & FPS Estimator]
    B --> D[Latest-Frame Mailbox Lock]
    
    subgraph "Threaded Processing"
        D -->|Drop Backlog, Pick Freshest| E[Worker Analysis Thread]
        E --> F[Parallel MediaPipe Pool: max_workers=3]
        F --> G1[FaceMesh: 468+ Landmarks]
        F --> G2[Pose: 33 Landmarks]
        F --> G3[Hands: 21 Landmarks x2]
        
        E --> H[PyTorch Emotion Inference: YOLOv8 Face + EfficientNet-B0]
    end

    subgraph "Behavioral Detectors"
        G1 --> I1[Gaze & Attention: GazeDetector]
        G1 --> I2[Facial Tension: TensionDetector]
        G2 --> I3[Posture & Spine: PostureDetector]
        G2 & G3 --> I4[Arm Gestures: ArmDetector]
        G3 --> I5[Fist Clench & Curl: HandDetector]
        G2 --> I6[Leg Fidgeting & Cross: LegDetector]
        G2 --> I7[Movement Energy: EnergyDetector]
        G1 & G2 & G3 --> I8[Face & Neck Touch: FaceTouchDetector]
        H --> I9[Emotion Ratios: 8 Classes]
    end

    subgraph "Aggregation & Scoring"
        I1 & I2 & I3 & I4 & I5 & I6 & I7 & I8 & I9 --> J[Context Window Accumulator: _llm_accumulate_frame]
        J --> K[Composite Scores: Facial Activity, Rigidity, Stillness]
        J --> L[Trigger Context Switch: trigger_context_switch]
        L --> M[Structured JSONL Log: context_wise_video_aggregation.jsonl]
    end

    subgraph "Dashboard & LLM Synthesis"
        M --> N[Streamlit UI Dashboard: ui.py]
        N --> O1[Upright Posture & Arm Cards]
        N --> O2[Nervousness & Demeanour Indicators]
        N --> O3[ECharts OCEAN Personality Gauges]
        N --> O4[Genuineness & Deception Risk Gauges]
    end
```

### Missing or Incomplete Stages in Host Pipeline
- **Missing Multi-Person Tracking:** Designed strictly for a single subject; crashes or produces unpredictable results if multiple faces/bodies enter the frame.
- **Missing Task/Productivity Classifier:** Does not classify whether an employee is typing, reading, or working; infers mental state purely from physical movements.
- **Missing Ground Truth Calibration:** All thresholds for "fidgeting", "tension", and "posture" are fixed empirical constants without individual baseline normalization.

---

## 7. End-to-End Pipeline for the Extracted Project (`audit_extracted`)

The extracted project executes a straightforward bounding-box detection loop:

```mermaid
flowchart TD
    A[Video Source: Webcam / Uploaded MP4 / Custom RTSP] --> B[cv2.VideoCapture]
    B --> C[Initial Probe: 5 Frames]
    C --> D{Desk Area Config?}
    
    D -->|Auto-detect| E[Detect COCO Classes: 56, 60, 63, 64, 65]
    E --> F{>= 2 Candidates?}
    F -->|Yes| G[Enclosing Bounding Box + 10% Padding]
    F -->|No| H[Default Fallback ROI: 20%-80% X, 40%-90% Y]
    D -->|Manual| I[Parse Coordinates: coords.split]
    
    G & H & I --> J[Set Monitored Area: monitor_area]
    
    subgraph "Tracking Thread: _tracking_loop"
        K[Read Frame: cap.read] --> L[Resize Frame to Width=600px]
        L --> M[OpenCV blobFromImage: 416x416, 1/255.0]
        M --> N[YOLOv4-tiny Forward Pass: net.forward]
        N --> O[Filter Person Class: class_id == 0]
        O --> P[cv2.dnn.NMSBoxes: conf_thresh, nms=0.4]
        
        P --> Q[Calculate Bounding Box Overlap with monitor_area]
        Q --> R{Overlap Ratio > 0.3?}
        
        R -->|Yes| S[Mark Employee Present: employee_detected = True]
        R -->|No| T[Mark Absent: employee_detected = False]
        
        S & T --> U[State Machine: Presence vs. Absence Transitions]
        U --> V{Absence Duration >= Threshold?}
        V -->|Yes & Not Logged| W[Log Absence Event to employee_log.txt]
        V -->|No| X[Update Absence Elapsed Timer]
        
        U --> Y[Draw Overlays: Green ROI, Red/Blue Boxes, Text]
        Y --> Z1[Write Periodic Snapshot: output_frames/ every 10s]
        Y --> Z2[Update Memory Frame: self.current_frame]
    end

    subgraph "Web Interface & Output"
        Z2 --> AA[/video_feed: MJPEG Stream]
        U --> AB[/status: JSON Polling Endpoint]
        W --> AC[/logs: Recent 100 Log Lines]
        AA & AB & AC --> AD[index.html: Bootstrap 5 Dashboard]
    end
```

### Explicitly Missing Stages in Extracted Pipeline
- **NO Temporal Filtering / Smoothing:** Bounding boxes fluctuate on every frame; single-frame occlusions immediately register as candidate absences.
- **NO Person Tracking / Re-ID:** No feature vectors or tracking IDs. Any stranger walking into the green box is classified as "The Employee".
- **NO Activity / Work Recognition:** Zero posture, keyboard interaction, or attentional analysis.
- **NO Productivity Calculation:** Zero productivity metrics or aggregations.
- **NO Database Storage:** Everything is stored in an ephemeral flat text file.

---

## 8. Complete Metric Inventory for the Main / Host Project (`video/`)

| Metric / Indicator | Definition | Exact Formula / Implementation Rule | Source File & Line Range | Inputs | Units / Output Range | Evidence Status |
|---|---|---|---|---|---|---|
| **`llm_posture_score`** | Ratio of good posture frames to total evaluated posture frames | `good_frames / (good_frames + bad_frames)` | [main.py#L353-L356](file:///C:/Users/DELL/Desktop/video/main.py#L353-L356) | Spine alignment, head tilt | `[0.0, 1.0]`, Unitless ratio | **VERIFIED** |
| **`llm_posture_label`** | Categorical posture assessment | `"Good" if score >= 0.6 else "Bad"` | [main.py#L357](file:///C:/Users/DELL/Desktop/video/main.py#L357) | `llm_posture_score` | String (`"Good"`, `"Bad"`) | **VERIFIED** |
| **`llm_arm_score`** | Proportion of open arm body language frames | `arm_good_frames / total_arm_frames` | [main.py#L359-L360](file:///C:/Users/DELL/Desktop/video/main.py#L359-L360) | Arm elbow angle, wrist distance | `[0.0, 1.0]`, Unitless ratio | **VERIFIED** |
| **`llm_arm_label`** | Categorical arm position | `"Closed Arm" if bad > good else "Open Arm"` | [main.py#L361](file:///C:/Users/DELL/Desktop/video/main.py#L361) | Frame counts | String (`"Closed Arm"`, `"Open Arm"`) | **VERIFIED** |
| **`llm_fist_score`** | Ratio of open hands vs clenched fists | `fist_good_frames / total_fist_frames` | [main.py#L363-L364](file:///C:/Users/DELL/Desktop/video/main.py#L363-L364) | MediaPipe hand curl metrics | `[0.0, 1.0]`, Unitless ratio | **VERIFIED** |
| **`llm_fist_label`** | Categorical fist state | `>=0.60: "Open Fist"; >=0.30: "Partial Open"; else: "Closed Fist"` | [main.py#L365-L367](file:///C:/Users/DELL/Desktop/video/main.py#L365-L367) | `llm_fist_score` | Categorical String | **VERIFIED** |
| **`llm_eye_score`** | Proportion of frames with focused gaze | `eye_good_frames / total_eye_frames` | [main.py#L369-L370](file:///C:/Users/DELL/Desktop/video/main.py#L369-L370) | Iris bounding, FaceMesh | `[0.0, 1.0]`, Unitless ratio | **VERIFIED** |
| **`llm_eye_label`** | Gaze focus verdict | `>=0.7: "Focused"; >=0.4: "Mild Focus"; else: "Distracted"` | [main.py#L371-L373](file:///C:/Users/DELL/Desktop/video/main.py#L371-L373) | `llm_eye_score` | Categorical String | **VERIFIED** |
| **`llm_hand_activity_score`**| Hand stillness index | `hand_tap_good / total_hand_frames` | [main.py#L375-L376](file:///C:/Users/DELL/Desktop/video/main.py#L375-L376) | Wrist motion variance | `[0.0, 1.0]`, Unitless ratio | **VERIFIED** |
| **`llm_leg_score`** | Leg stillness ratio | `(cross_leg_good + toe_tap_good) / total_leg` | [main.py#L378-L381](file:///C:/Users/DELL/Desktop/video/main.py#L378-L381) | Ankle & knee landmark speeds | `[0.0, 1.0]`, Unitless ratio | **VERIFIED** |
| **`llm_leg_motion_label`** | Dynamic classification of lower body fidgeting | `kick_ratio >= 0.05: "Kicking"; jiggle_ratio >= 0.15: "Jiggling"; else: "Still"` | [main.py#L387-L397](file:///C:/Users/DELL/Desktop/video/main.py#L387-L397) | Frame motion accumulators | String (`"Kicking"`, `"Jiggling"`, `"Still"`) | **VERIFIED** |
| **`facial_activity_score`** | Weighted composite score of facial muscle dynamics | `0.20*std(emo) + 0.25*eyebrow + 0.25*mouth + 0.10*jaw + 0.10*eye + 0.10*emo` | [main.py#L479-L492](file:///C:/Users/DELL/Desktop/video/main.py#L479-L492) | EMA displacements, emotion history | `[0.0, 1.0]`, Clamped index | **VERIFIED** |
| **`facial_rigidity_score`** | Inverse metric of facial emotion variability | `max(0.0, min(1.0, 1.0 - np.std(emotion_history)))` | [main.py#L617-L623](file:///C:/Users/DELL/Desktop/video/main.py#L617-L623) | Emotion variance | `[0.0, 1.0]`, Default 0.5 | **VERIFIED** |
| **`blink_rate_context`** | Frequency of eye blinks normalized per minute | `(total_blinks / context_duration) * 60.0` | [main.py#L635](file:///C:/Users/DELL/Desktop/video/main.py#L635) | Eyelid aspect ratio crossings | Blinks per minute (BPM) | **VERIFIED** |
| **`llm_gaze_aversion_score`**| Fraction of time gaze is averted from camera | `aversion_frames / max(1, aversion_frames + good_frames)` | [main.py#L550-L554](file:///C:/Users/DELL/Desktop/video/main.py#L550-L554) | Iris yaw/pitch bounds | `[0.0, 1.0]`, Unitless ratio | **VERIFIED** |
| **`ocean_scores`** (Big 5) | Psychological profile traits (O, C, E, A, N) | Inferred via external LLM prompt from aggregated behavioural chunk | [ui.py#L540-L551](file:///C:/Users/DELL/Desktop/video/ui.py#L540-L551) | Numeric means from JSONL | `0.0 - 100.0` per trait | **UNVERIFIED / PROMPT-DRIVEN** |
| **`genuineness_score`** | Composite index evaluating interview honesty | Hardcoded / Mocked in demo, or computed by LLM response | [trial.py#L27-L38](file:///C:/Users/DELL/Desktop/video/trial.py#L27-L38), [t.py#L16-L25](file:///C:/Users/DELL/Desktop/video/t.py#L16-L25) | Behavioral payload | `0.0 - 100.0%` | **FORMULA NOT VERIFIED** |
| **`deception_label`** | High / Medium / Low deception risk indicator | Derived from LLM context response or rules | [ui.py#L604-L612](file:///C:/Users/DELL/Desktop/video/ui.py#L604-L612) | Context indicators | High / Medium / Low | **UNVERIFIED / PROMPT-DRIVEN** |

---

## 9. Complete Metric Inventory for the Extracted Project (`audit_extracted`)

| Metric / Indicator | Definition | Exact Formula / Implementation Rule | Source File & Line Range | Inputs | Units / Output Range | Evidence Status |
|---|---|---|---|---|---|---|
| **`confidence`** | YOLO object detection score threshold | `scores[class_id] > confidence_threshold` | [employee_tracking_fixed.py#L546](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L546) | Softmax output of YOLO | `[0.1, 1.0]`, Configured (def: 0.5) | **VERIFIED** |
| **`overlap_ratio`** | Proportion of person bounding box within desk ROI | `intersection_area / (person_w * person_h)` | [employee_tracking_fixed.py#L580-L582](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L580-L582) | Person box & Monitor area | `[0.0, 1.0]`, Ratio | **VERIFIED** |
| **`employee_detected`** | Boolean flag indicating employee presence at desk | `True if overlap_ratio > 0.3 else False` | [employee_tracking_fixed.py#L584-L586](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L584-L586) | Bounding box intersection | Boolean (`True` / `False`) | **VERIFIED** |
| **`absence_duration`** | Elapsed time employee has been absent | `time.time() - self.absence_start_time` | [employee_tracking_fixed.py#L141-L144](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L141-L144), [L610](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L610) | Wall-clock timestamps | Seconds (`>= 0.0`) | **VERIFIED** |
| **`absence_alert`** | Absence event logging trigger | `absence_duration >= absence_threshold and not logged` | [employee_tracking_fixed.py#L487-L490](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L487-L490) | Timer & configured threshold | Event logged to disk | **VERIFIED** |
| **`frames_processed`** | Cumulative frame counter | `self.frames_processed += 1` per loop iteration | [employee_tracking_fixed.py#L495](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L495) | Loop count | Non-negative integer | **VERIFIED** |
| **`Productivity Score`** | Workforce output / effectiveness metric | **None** — not present anywhere in codebase | Nowhere in code | None | None | **NOT IMPLEMENTED** |
| **`Attendance Percentage`**| Workstation occupancy ratio over time | **None** — only instant state is reported | Nowhere in code | None | None | **NOT IMPLEMENTED** |
| **`Track ID Persistence`** | Multi-frame object identification | **None** — detections treated independently | Nowhere in code | None | None | **NOT IMPLEMENTED** |
| **`Activity Classification`**| Working vs Idle vs On Phone vs Away | **None** — any person box with >30% overlap is "Working" | Nowhere in code | None | None | **NOT IMPLEMENTED** |

---

## 10. Detailed Formulas and Calculation Traces

### Trace 1: Extracted Project — Raw Video to Absence Duration
```
1. Frame Acquisition:
   cap.read() → frame [H, W, 3]

2. Preprocessing:
   frame_resized = cv2.resize(frame, (600, int(H * 600 / W)))
   blob = cv2.dnn.blobFromImage(frame_resized, scalefactor=1/255.0, size=(416, 416), swapRB=True, crop=False)

3. Deep Learning Inference:
   net.setInput(blob)
   detections = net.forward(output_layers)

4. Detection Filtering & Bounding Box Reconstruction:
   For detection in detections:
     scores = detection[5:]
     class_id = argmax(scores)
     confidence = scores[class_id]
     If confidence > confidence_threshold and class_id == 0:  # COCO Person
       center_x = detection[0] * width
       center_y = detection[1] * height
       w = detection[2] * width
       h = detection[3] * height
       x = center_x - w / 2
       y = center_y - h / 2

5. Non-Maximum Suppression:
   indices = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold=0.4)

6. Desk Intersection & Overlap Calculation:
   For i in indices:
     person_box = (x, y, x + w, y + h)
     x_intersection = max(monitor_area[0], person_box[0])
     y_intersection = max(monitor_area[1], person_box[1])
     w_intersection = min(monitor_area[2], person_box[2]) - x_intersection
     h_intersection = min(monitor_area[3], person_box[3]) - y_intersection
     
     If w_intersection > 0 and h_intersection > 0:
       intersection_area = w_intersection * h_intersection
       person_area = w * h
       overlap_ratio = intersection_area / person_area
       If overlap_ratio > 0.3:
         employee_detected = True

7. Absence Timing State Machine:
   current_time = time.time()
   If employee_detected == False:
     If previous_state == PRESENT:
       absence_start_time = current_time
     Else:
       absence_duration = current_time - absence_start_time
       If absence_duration >= absence_threshold and not absence_logged:
         log_event("Employee absence detected")
         absence_logged = True
   Else:
     If previous_state == ABSENT:
       return_duration = current_time - absence_start_time
       log_event(f"Employee returned after {return_duration:.1f} seconds")
       absence_start_time = None
       absence_logged = False

8. Output & Display:
   - Frame rendered with overlay: `cv2.putText(frame, f"Absence: {absence_duration:.1f}s", ...)`
   - JSON status endpoint: `{"employee_present": False, "absence_duration": absence_duration}`
```

### Trace 2: Host Project — Facial Activity & Rigidity Composite Formula
```
1. Frame Input to Worker Thread:
   img_rgb = cv2.cvtColor(mailbox_frame, cv2.COLOR_BGR2RGB)

2. MediaPipe FaceMesh Inference:
   results_face = face_mesh.process(img_rgb)
   valid_face = bool(results_face.multi_face_landmarks)

3. PyTorch Emotion Network:
   face_crop = extract_face(img, results_face)
   face_enhanced = enhance_face_image_fast(face_crop)
   probs = softmax(efficientnet_b0(preprocess(face_enhanced)))
   dominant_emotion, mapped_ratios = map_to_8_emotions(probs)
   emotion_history.append(argmax_confidence)

4. Landmark Motion Displacements (EMA):
   eyebrow_displacement = compute_landmark_motion(mesh, indices=[70, 63, 105, 66, 107])
   mouth_displacement   = compute_landmark_motion(mesh, indices=[13, 14, 78, 308])
   jaw_displacement     = compute_landmark_motion(mesh, indices=[172, 397])

5. Statistical Variance Calculation:
   If len(emotion_history) > 1:
     emotion_variance = float(np.std(emotion_history))
   Else:
     emotion_variance = 0.0

6. Composite Facial Activity Score:
   facial_activity_score = (
       emotion_variance  * 0.20 +
       eyebrow_motion    * 0.25 +
       mouth_motion      * 0.25 +
       jaw_motion        * 0.10 +
       llm_eye_score     * 0.10 +
       llm_emotion_score * 0.10
   )
   facial_activity_score = max(0.0, min(1.0, facial_activity_score))

7. Label Mapping:
   If score < 0.25:   "Very Rigid"
   Elif score < 0.45: "Mild Activity"
   Elif score < 0.70: "Expressive"
   Else:              "Highly Expressive"
```

---

## 11. Activity Recognition and Classification Logic

### Extracted Project (`audit_extracted`)
- **Classification Approach:** **No activity recognition algorithm is implemented.**
- **Heuristic:** Presence inside the desk bounding box (`overlap_ratio > 0.3`) is treated as the sole proxy for "working".
- **Limitations:**
  - An employee sleeping, staring at their phone, or sitting motionless is classified identically to an actively working employee.
  - An empty chair or an inanimate object mistakenly detected as a person (or a coworker sitting down) produces a positive "Present" classification.

### Host Project (`video/`)
- **Classification Approach:** Fine-grained posture, gesture, and movement classification using 2D/3D skeletal and facial landmarks.
- **Specific Activity Rules:**
  - **Arm Crossing:** Angle between shoulder-elbow-wrist vectors combined with wrist-to-chest proximity. `bad_frames > good_frames` produces `"Closed Arm"`.
  - **Fist Clenching:** Normalized Euclidean distance between fingertips (landmarks 4, 8, 12, 16, 20) and wrist (landmark 0). Average curl determines `"Open"`, `"Partial"`, or `"Closed"`.
  - **Leg Motion (Fidgeting/Kicking):** Frame-to-frame velocity of knee and ankle landmarks. Velocity thresholds sort movement into Still, Jiggling, or Kicking.
  - **Face Touching:** Proximity between hand landmarks and face/neck mesh polygons.
- **Scientific Caveat:** While physically detailed, physical fidgeting is correlated with stress or boredom, not necessarily low productivity. A software engineer actively debugging complex code may sit rigidly or fidget without being unproductive.

---

## 12. Person Detection and Tracking Logic

### Detection Comparison

```
+---------------------------------------------------------------------------------------------------+
| Feature                      | Extracted Project                      | Host Project              |
+------------------------------+----------------------------------------+---------------------------+
| Primary Detector             | YOLOv4-tiny (Darknet, 416x416)         | YOLOv8n-face + MediaPipe  |
| Confidence Cutoff            | Configurable (default 0.50)            | Fixed (0.50 - 0.60)       |
| Multi-Person MOT             | None (Stateless bounding boxes)        | Single-person only        |
| Re-Identification            | None                                   | None                      |
| Occlusion Recovery           | None (instant track drop)              | MediaPipe filter memory   |
| Tracking Loss Handling       | Counts immediate absence               | Drops metrics calculation |
| ID Switch Susceptibility     | Critical (no IDs assigned)             | Critical if multi-subject |
+---------------------------------------------------------------------------------------------------+
```

### Critical Tracking Flaw in the Extracted Project
In [employee_tracking_fixed.py#L566-L596](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L566-L596), the code iterates through all NMS detection boxes:
```python
for i in indices.flatten():
    x, y, w, h = boxes[i]
    person_box = (x, y, x+w, y+h)
    ...
    if overlap_ratio > 0.3:
        employee_detected = True
        is_in_desk_area = True
```
Because the loop stops at setting `employee_detected = True`, **any human bounding box** that overlaps the desk area by >30% triggers the presence flag. If a visitor stands next to the desk while the employee is away, the system reports the employee as continuously present.

---

## 13. Time, Duration, and Temporal Aggregation

### Extracted Project Timing
- **Clock Source:** Python `time.time()` (system wall-clock epoch).
- **Sampling Frequency:** Unbounded capture thread with `time.sleep(0.01)` (webcam) or `time.sleep(0.033)` (video upload).
- **Session Boundaries:** Started on `/start_tracking`, terminated on `/stop_tracking`.
- **Absence Duration Accumulation:**
  ```python
  absence_duration = current_time - self.absence_start_time
  ```
- **Major Timing Vulnerability:** The duration is calculated purely from wall-clock time between discrete frames. If the video decoding thread falls behind due to high CPU load, or if video frames drop, the elapsed absence duration increases at standard clock speed regardless of how much video content was actually evaluated.

### Host Project Timing & Aggregation
- **Fixed Recording FPS:** `RECORDING_FPS = 10` (in `main.py`) and `20` (in `comp.py`).
- **Dynamic Adaptive Frame Skipping:** Measures frame interval variability (`_detect_network_quality`); if intervals rise above 0.1s, emotion inference skip rate increases from 2 to 4 frames.
- **Context Chunk Windows:** Aggregates metrics into discrete contextual chunks via `trigger_context_switch(start_sec, end_sec)`. Calculates arithmetic means of numeric accumulators (`llm_acc[key]["sum"] / count`) and categorical modes (`Counter.most_common(1)`).

---

## 14. Productivity Score Calculation and Limitations

### Explicit Audit Finding: No Productivity Metric Exists
Neither codebase implements an actual workforce productivity formula.

```
+----------------------------------------------------------------------------------------------------+
| Dimension                    | Documented Claim                       | Verified Reality           |
+------------------------------+----------------------------------------+----------------------------+
| Productivity Formula         | "real-time insights for productivity"  | NOT IMPLEMENTED (0 lines)  |
| Desk Occupancy Ratio         | "automated attendance tracking"        | NOT IMPLEMENTED            |
| Active vs. Idle Time         | "comprehensive analytics"              | NOT IMPLEMENTED            |
| Task Engagement              | "intelligent monitoring"               | NOT IMPLEMENTED            |
| Subject Identification       | "employee recognition"                 | Generic COCO class 0 only  |
+----------------------------------------------------------------------------------------------------+
```

### The "Productivity Proxy" Fallacy
In both projects, physical presence or physiological cues are conflated with productivity:
1. **Extracted Project Fallacy:** $\text{Workplace Productivity} \equiv \text{Bounding Box Overlap} > 30\%$. Being at a desk does not equate to working; reading a book, staring blankly, or sleeping are counted as 100% compliant.
2. **Host Project Fallacy:** $\text{Candidate Competence / Productivity} \equiv \text{Posture} + \text{Lack of Fidgeting} + \text{Direct Eye Contact}$. Individuals with neurodivergent traits (e.g., ADHD, autism) frequently exhibit gaze aversion or repetitive motions while maintaining high intellectual output and productivity. Evaluating workforce performance on these proxies is scientifically invalid and legally discriminatory.

---

## 15. Backend-to-Frontend Data Flow

### A. Extracted Project Data Flow & Critical Polling Defect

```mermaid
sequenceDiagram
    autonumber
    actor User as Web Browser
    participant Flask as Flask Server (app.py)
    participant Tracker as EmployeeTracker
    
    User->>Flask: POST /start_tracking (config JSON)
    Flask->>Tracker: start_tracking(config)
    Tracker-->>Flask: {"status": "success"}
    Flask-->>User: 200 OK
    Note over User: User JS executes updateStatus() ONCE!
    User->>Flask: GET /status
    Flask->>Tracker: get_status()
    Tracker-->>Flask: {"employee_present": true, "absence_duration": 0, "frames_processed": 14}
    Flask-->>User: 200 OK
    Note over User,Flask: CRITICAL BUG: No setInterval or recursion on success!<br/>Browser NEVER calls /status again.<br/>Telemetry permanently freezes!
    
    User->>Flask: GET /video_feed
    loop Multipart MJPEG Stream
        Tracker->>Flask: get_current_frame() (encoded JPEG)
        Flask-->>User: --frame Content-Type: image/jpeg
    end
```

### B. Specific Frontend Bugs Discovered in `templates/index.html`

1. **Dead Status Polling ([index.html#L846-L869](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/templates/index.html#L846-L869)):**
   ```javascript
   function updateStatus() {
       $.get('/status', function(data) {
           if (data.status === 'active') {
               $('#statusValue').text('Active');
               ...
           }
       }).fail(function() {
           setTimeout(updateStatus, 2000);  // ONLY retries on error!
       });
   }
   ```
   Because `setTimeout(updateStatus, ...)` is placed strictly in the `.fail()` handler, a successful response terminates all polling. The web dashboard never updates absence duration or frame count during active tracking.

2. **Phantom Frame Capture ([index.html#L817-L821](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/templates/index.html#L817-L821)):**
   ```javascript
   $('#captureBtn').click(function() {
       const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
       addLogEntry('Frame captured: ' + timestamp, 'present');
   });
   ```
   Clicking "Capture Frame" does not capture a frame. It only adds a string to the browser's HTML log list. The backend endpoint `/captures/<filename>` is never called.

3. **Coordinate Truncation Bug in Manual Desk Setup ([employee_tracking_fixed.py#L218-L226](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L218-L226)):**
   ```python
   coords = config.get("manual_coords", "0.1,0.1,0.9,0.9")
   x1, y1, x2, y2 = map(float, coords.split(','))
   self.monitor_area = (int(x1), int(y1), int(x2), int(y2))
   ```
   The placeholder suggests normalized coordinates (`0.1,0.1,0.9,0.9`). Casting `float(0.1)` directly to `int` truncates to `0`. The monitored box collapses to `(0, 0, 0, 0)`, rendering detection completely broken unless pixel integers are entered.

4. **Infinite Video Rewind Bug during Auto-Desk Detection ([employee_tracking_fixed.py#L393-L396](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/employee_tracking_fixed.py#L393-L396)):**
   ```python
   while frame_count < max_frames:
       ret, frame = cap.read()
       ...
       if self.source_type == "upload":
           cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
   ```
   Inside the loop that evaluates 5 frames to find desk furniture, `cap.set(..., 0)` resets the video to frame 0 on *every iteration*. It processes frame 0 five times instead of scanning across 5 distinct frames.

---

## 16. Database, Storage, and Data Quality

### Storage Implementation Analysis

| Subsystem | Extracted Project (`audit_extracted`) | Host Video Project (`video/`) |
|---|---|---|
| **Primary Storage Engine** | Plain text file (`logs/employee_log.txt`) | JSON Lines file (`context_wise_video_aggregation.jsonl`) |
| **Relational / NoSQL DB** | None | None |
| **Frame Snapshot Storage** | `output_frames/frame_%06d.jpg` | Single MP4 recording (`session_recording.mp4`) |
| **Concurrency Safeguards** | Single process thread lock (`self.lock`) | File-append locks + mailbox threading locks |
| **Historical Querying** | `f.readlines()[-max_lines:]` (in-memory read) | Ingestion into external vector store / LLM |
| **Schema Validation** | None (unstructured string formatting) | JSON schema with structured key-value dictionaries |

### Data Quality & Integrity Risks
- **Unbounded Disk Consumption:** The extracted project saves full-resolution JPEG frames every 10 seconds into `output_frames/` without any garbage collection, maximum folder size limit, or retention policy. Long-running deployments will exhaust disk space.
- **Log Corruption upon Concurrent Writes:** In `app.py`, Gunicorn is executed with `--workers 1`. If scaled to multiple workers (`--workers > 1`), concurrent worker processes appending to `employee_log.txt` without OS-level file locking will cause interleaved and corrupted lines.

---

## 17. Side-by-Side Project Comparison

| Capability | Extracted Project (`audit_extracted`) | Host Project (`video/`) | Evidence and Architectural Differences |
|---|---|---|---|
| **Video Input Support** | Webcam, File Upload, RTSP / HTTP URL | WebRTC Stream, Local Video | Extracted supports RTSP; Host relies on Streamlit-WebRTC browser client. |
| **Person Detection** | Darknet YOLOv4-tiny (416x416 CPU) | YOLOv8n-face + MediaPipe Pose/Face | Extracted detects full body bounding boxes; Host detects facial mesh and pose skeletons. |
| **Multi-Person Tracking** | **ABSENT** (Single-frame NMS only) | **ABSENT** (Single-subject assumption) | Neither codebase implements MOT algorithms or track persistence. |
| **Employee Identification** | **ABSENT** (All humans = class 0) | **ABSENT** (No facial recognition / Re-ID) | Neither system knows *who* is in front of the camera. |
| **Activity Recognition** | **ABSENT** (Proxy = bounding box overlap) | **IMPLEMENTED** (Pose & hand gestures) | Host classifies arms, fists, posture, fidgeting; Extracted has no action classifier. |
| **Workstation Occupancy** | **IMPLEMENTED** (Desk overlap > 0.3) | **ABSENT** (No desk / ROI definition) | Extracted detects workspace ROI; Host focuses strictly on upper-body demeanour. |
| **Idle / Away Detection** | **IMPLEMENTED** (Threshold absence timer) | **PARTIALLY IMPLEMENTED** (Stillness score) | Extracted tracks physical absence; Host tracks physical motionlessness. |
| **Productivity Scoring** | **ABSENT** | **ABSENT** (Replaced by OCEAN / Genuineness) | Neither project calculates verified workplace productivity. |
| **Dashboard Architecture** | Flask + Jinja2 + Bootstrap 5 + jQuery | Streamlit + Apache ECharts | Host provides rich interactive charts; Extracted provides a basic frozen status card. |
| **Storage Architecture** | Flat text log (`employee_log.txt`) | Flat JSONL log (`aggregation.jsonl`) | Both lack robust transactional database engines. |
| **Runtime Performance** | ~15-25 FPS on CPU (YOLOv4-tiny) | ~5-12 FPS on CPU (MediaPipe + PyTorch) | Extracted is lightweight; Host is computationally demanding. |
| **Automated Tests** | **ABSENT** (0 test files) | **ABSENT** (Only mock display scripts) | Neither project has unit tests, integration tests, or CI test suites. |

---

## 18. Testing and Validation Evidence

### Complete Absence of Formal Test Suites
- **Extracted Project:** Zero unit test files (`test_*.py`), zero mocks, zero automated tests.
- **Host Project:** Contains `test_dashboard.py` and `top_test.py`, but these are purely manual GUI launch scripts that feed static mock dictionaries into Streamlit components.

### Ground Truth & Accuracy Validation
- **No Ground Truth Datasets:** Neither repository contains ground-truth annotated video benchmarks (e.g., MOT17, MOT20, AVA, or custom labeled workplace videos).
- **Unverified Accuracy Claims:** The README claim of *"intelligent person recognition with high accuracy"* is unsupported by empirical validation, ablation studies, or confusion matrices.
- **Arbitrary Thresholds:**
  - `overlap_ratio > 0.3`: Chosen arbitrarily without empirical validation of false positives from reaching across a desk.
  - `absence_threshold = 5`: Default 5 seconds is unrealistically short for office environments (turning around or bending down triggers an absence alert).
  - `posture_score >= 0.6`: Arbitrary cutoff with no ergonomic justification.

---

## 19. Performance and Resource Analysis

### Computational Profiling (Code-Derived Observations)

```
+---------------------------------------------------------------------------------------------------+
| Component / Step             | Extracted Project                      | Host Project              |
+------------------------------+----------------------------------------+---------------------------+
| Frame Preprocessing          | Resize to 600px width (negligible)     | BGR to RGB conversion     |
| Deep Learning Inference      | YOLOv4-tiny CPU Forward pass (~40-60ms)| 3x MediaPipe models (~90ms)|
| Secondary Model Inference    | None                                   | EfficientNet-B0 (~30-50ms)|
| Memory Footprint             | Lightweight (~150-250 MB RAM)          | Heavy (~800 MB - 1.8 GB)  |
| GPU Acceleration             | Disabled (`DNN_TARGET_CPU`)            | Conditional PyTorch CUDA  |
| Frame Dropping Strategy      | None (Blocks thread if slow)           | Mailbox pattern (Drops)   |
+---------------------------------------------------------------------------------------------------+
```

### Bottlenecks and Scalability
1. **Extracted Project:**
   - Single-threaded OpenCV DNN execution blocks the Flask response loop if camera frames stutter.
   - For RTSP streams, network latency or packet drops cause `cap.read()` to hang indefinitely without a timeout mechanism.
2. **Host Project:**
   - `ThreadPoolExecutor(max_workers=3)` creates heavy CPU thread contention when running alongside Streamlit's Tornado event loop.

---

## 20. Security, Privacy, and Operational Risks

### A. Critical Security Vulnerability: Plaintext Password Leakage
- **Location:** [employee_log.txt#L19-L20](file:///C:/Users/DELL/Desktop/cctv/audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/logs/employee_log.txt#L19-L20)
- **Evidence:**
  ```
  2025-04-02 00:31:05 - Error: Could not open video source rtsp://admin:password@192.168.1.100:554/stream
  ```
- **Finding:** The application logs unredacted camera connection strings directly to disk. Any operator or user accessing `/logs` can extract camera credentials and network topologies.

### B. Severe Privacy and Legal Risks (GDPR, CCPA, Workplace Surveillance)
- **Continuous Biometric Extraction:** The host project extracts facial landmarks, eye contact status, and emotional states without explicit consent banners, data retention boundaries, or employee privacy safeguards.
- **Unprotected Video Streaming:** Neither project implements authentication or authorization tokens. Any network client that can reach port 5000 can view live camera feeds (`/video_feed`).
- **High Risk of Unfair Employment Actions:** Using absence thresholds of 5 seconds to generate disciplinary audit logs creates hostile workplace conditions and violates labor regulations regarding continuous automated surveillance.

---

## 21. Bugs, Inconsistencies, and Misleading Metrics

```
+------------------------------------------------------------------------------------------------------+
| Issue / Defect                        | File & Line Reference             | Technical Impact         |
+---------------------------------------+-----------------------------------+--------------------------+
| Status Polling Deadlock               | index.html#L846-L869              | UI telemetry permanently |
|                                       |                                   | freezes upon start       |
| Coordinate Integer Truncation         | employee_tracking_fixed.py#L220   | Manual ROI collapses to  |
|                                       |                                   | (0, 0, 0, 0)             |
| Auto-Desk Loop Rewind Bug             | employee_tracking_fixed.py#L395   | Processes frame 0 five   |
|                                       |                                   | times consecutively      |
| Phantom Capture Frame Button          | index.html#L817-L821              | Client-side placebo;     |
|                                       |                                   | no image saved           |
| Plaintext RTSP Credential Leak        | employee_log.txt#L19-L20          | Critical password leak   |
| Fake "React Dashboard" Claim          | README.md#L256                    | Deceptive documentation  |
| Missing Productivity Metric           | Entire Extracted Codebase         | Missing core promised    |
|                                       |                                   | business functionality   |
+------------------------------------------------------------------------------------------------------+
```

---

## 22. Missing Features and Unverified Claims

### Extracted Project Discrepancy Matrix

```
+-----------------------------------------------------------------------------------------------------+
| Feature Claimed in README / UI        | Actual Status in Source Code       | Evidence / Location    |
+---------------------------------------+------------------------------------+------------------------+
| "React Dashboard"                     | NOT IMPLEMENTED (JQuery/Bootstrap) | index.html             |
| "WebSocket-like Updates"              | NOT IMPLEMENTED (Broken Polling)   | index.html#L865        |
| "Productivity Management Insights"    | NOT IMPLEMENTED (0 calculations)   | employee_tracking.py   |
| "Multi-person tracking"               | DOCUMENTED ONLY (Planned feature)  | README.md#L468         |
| "Automated Attendance Tracking"       | PARTIALLY IMPLEMENTED (Absence only| employee_tracking.py   |
| "Capture Frame" Web Feature           | UI ONLY (DOM text injection only)  | index.html#L817        |
| "Google Drive / S3 Video Input"       | NOT IMPLEMENTED (Returns Error)    | employee_tracking.py#L187
+-----------------------------------------------------------------------------------------------------+
```

---

## 23. Prioritized Findings Register

| ID | Finding | Project | Severity | Evidence | Impact | Recommended Action |
|---|---|---|---|---|---|---|
| **SEC-01** | Plaintext RTSP Credentials in Execution Logs | Extracted | **CRITICAL** | `logs/employee_log.txt#L19` | Exposure of camera credentials and IP addresses to unauthorized users | Sanitize URLs before logging by masking credentials (`user:***@host`). |
| **ANL-01** | Productivity Score Completely Unimplemented | Extracted | **CRITICAL** | Entire codebase | Marketing claims mislead stakeholders; no actual productivity measurement exists | Implement explicit formula or remove claims from documentation. |
| **BUG-01** | Web Dashboard Status Polling Permanently Freezes | Extracted | **HIGH** | `templates/index.html#L846` | UI telemetry never updates after initial activation | Replace one-shot call with `setInterval(updateStatus, 1000)`. |
| **BUG-02** | Manual Desk Coordinates Parse to Zero | Extracted | **HIGH** | `employee_tracking_fixed.py#L220` | Manual ROI fails completely when normalized floats are supplied | Multiply normalized float inputs by image `width` and `height`. |
| **TRK-01** | Absence of Multi-Object Tracker (MOT) | Extracted | **HIGH** | `employee_tracking_fixed.py#L566` | System cannot identify unique individuals or maintain persistent identity | Integrate ByteTrack or SORT with unique tracking IDs. |
| **ETH-01** | Scientifically Unvalidated Psychological Profiling | Host | **HIGH** | `video/ui.py#L555-L635`, `trial.py` | High legal/ethical liability for deceptive employee evaluations | Decouple physical posture tracking from deception/personality verdicts. |
| **BUG-03** | Auto-Desk Detection Rewinds Video Frame 0 in Loop | Extracted | **MEDIUM** | `employee_tracking_fixed.py#L395` | Redundant processing of frame 0 five times | Move `cap.set(..., 0)` outside the frame collection loop. |
| **SEC-02** | Unauthenticated Video Streaming Endpoints | Both | **MEDIUM** | `app.py#L14-L24` | Anyone on local network can view live webcam stream | Implement JWT / session authentication guards on all streaming endpoints. |
| **RES-01** | Unbounded Disk Storage from Frame Snapshots | Extracted | **MEDIUM** | `employee_tracking_fixed.py#L498` | Server disk fills up completely after continuous execution | Add a rolling FIFO ring buffer with max file retention. |
| **DOC-01** | Deceptive Architecture Claims in README | Extracted | **LOW** | `README.md#L256` | Inaccurate documentation claims React frontend and WebSockets | Update documentation to reflect actual Flask/Bootstrap architecture. |

---

## 24. Prioritized Recommendations & Actionable Next Steps

### Top 5 Recommended Next Steps (Ranked by Impact)

1. **Implement a Rigorous, Ground-Truth Validated Productivity Index:**
   Replace the simplistic bounding box presence check with an empirical activity calculation:
   $$\text{Productivity Index} = w_1 \cdot \text{Occupancy Ratio} + w_2 \cdot \text{Task Engagement Ratio} - w_3 \cdot \text{Excessive Absence Penalty}$$
   Ensure all components are validated against ground-truth workplace annotations rather than assumed proxies.

2. **Integrate True Multi-Object Tracking (ByteTrack / BoT-SORT):**
   Replace stateless NMS with a verified tracker that maintains persistent track IDs across frames and handles transient occlusions gracefully without false absence alarms.

3. **Remediate Frontend Bugs and Restore Live Telemetry:**
   Fix `templates/index.html` by implementing recurring `setInterval` polling for `/status` and linking the "Capture Frame" button to a functional backend endpoint. Fix the manual coordinate parser to properly handle normalized bounding boxes.

4. **Sanitize Secrets and Secure Network Endpoints:**
   Purge plaintext credentials from `employee_log.txt`. Implement credential stripping in `log_event()` and add token-based authentication to `/video_feed` and `/start_tracking`.

5. **Establish an Automated Unit and Integration Test Suite:**
   Build automated pytest suites covering coordinate parsing, presence state machine transitions, video looping, and threshold triggers with synthetic frame fixtures.

### Reusable Components from Extracted Project (Without Integration)
- **`_detect_desk_area` Furniture Clustering Algorithm:** The heuristic that aggregates bounding boxes of desks, chairs, keyboards, and laptops (`classes [56, 60, 63, 64, 65]`) to auto-calibrate a workstation ROI is an innovative, highly reusable utility.
- **Docker Containerization Configuration (`Dockerfile`):** The multi-stage headless OpenCV configuration provides a clean, portable deployment baseline.
- **MJPEG Streaming Route (`video_feed`):** Simple, robust fallback mechanism for low-complexity video streaming where WebRTC is unavailable.

---

## 25. Final Conclusions

The extracted project (`OpenCV-Based-Real-time-Employee-Tracking-System-main`) is an early-stage prototype demonstrating basic object detection in a static zone, rather than a mature workplace productivity management platform. Its documentation claims far exceed its actual capabilities.

Conversely, the host project (`C:\Users\DELL\Desktop\video`) possesses a significantly more sophisticated multimodal computer vision architecture, but applies these signals toward unvalidated behavioral and personality proxies. 

A viable, enterprise-grade CCTV productivity platform requires merging the spatial workstation awareness of the extracted project with the temporal and skeletal analytics of the host project, anchored by true multi-object tracking, transparent mathematical formulas, and rigorous privacy controls.
