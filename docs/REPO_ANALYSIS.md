# Repository Analysis

## 1. @vladmandic/human (`c:/PJT/external/human-main`)
- **Languages:** JavaScript, TypeScript
- **Supported Runtimes:** Browser (WASM, WebGL, WebGPU) and Node.js (>= 14.0.0 via `@tensorflow/tfjs-node` or `tfjs-node-gpu`).
- **APIs:** Exposes ESM and CommonJS modules for tasks like face detection, body pose, emotion detection, and hand tracking.
- **Capabilities & How it works:** It uses TensorFlow.js to run various pre-trained models to extract spatial features from images or video frames.
- **Limitations:** Purely a CV feature extractor. Does not natively produce complex behavioral scoring or interaction metrics over time.
- **Usage Strategy:** Reuse directly via a Node.js adapter worker for asynchronous frame processing. It should NOT be used for NTS scoring directly, and its output should be normalized into the project's internal schema.

## 2. Realtime Meeting Intelligence (`c:/PJT/external/realtime-meeting-intelligence-main`)
- **Languages:** C# (.NET Framework), C++, Python.
- **Supported Runtimes:** Windows Server/Nodes (for Teams Bot), Linux/Windows (for Zoom Bot).
- **APIs:** Microsoft Graph / PSI, Zoom Meeting SDK.
- **Capabilities & How it works:** Captures raw audio and video streams from live Zoom/Teams meetings using bots, then fans out the media over secure tunnels to a Python stream processor.
- **Limitations:** Polyglot stack with heavy infrastructure dependencies.
- **Usage Strategy:** Do NOT reuse directly in the MVP. Its architecture serves as a reference pattern for Phase 15 (meeting bot ingestion), where bots stream media to the common Python backend.
