"""View 01: Live Annotated CCTV View.

Renders real-time video stream preview with dynamic Level-of-Detail (LOD)
overlay controls, stream health telemetry, and camera switcher.
"""

from typing import Any, Dict
import streamlit as st
from src.frontend.components.api_client import WBPISApiClient


def render(client: WBPISApiClient, camera_id: str) -> None:
    st.subheader("📹 View 01: Live Annotated CCTV Stream")
    st.markdown(
        "Real-time visual verification of spatial zone occupancy, person detection, "
        "and pseudonymized trajectory tracking. Overlay conforms to strict privacy boundaries."
    )

    # 0. Upload Video for Analysis
    with st.expander("📤 Upload Custom Workplace Video (.mp4, .avi, .mov)", expanded=False):
        uploaded_file = st.file_uploader(
            "Select a recorded CCTV video to analyze:",
            type=["mp4", "avi", "mov", "mkv"],
            key="view01_video_upload"
        )
        if uploaded_file is not None:
            c_up1, c_up2 = st.columns([2, 1])
            with c_up1:
                st.caption(f"📁 **Selected File:** `{uploaded_file.name}` ({(len(uploaded_file.getvalue()) / (1024 * 1024)):.1f} MB)")
            with c_up2:
                needs_up = st.session_state.get("active_analyzed_video") != uploaded_file.name
                btn_upload = st.button("🚀 Analyze Uploaded Video", type="primary", use_container_width=True, key="btn_upload_view01")
                if needs_up or btn_upload:
                    with st.spinner("Uploading and initializing video perception pipeline..."):
                        try:
                            res = client.upload_video(
                                file_bytes=uploaded_file.getvalue(),
                                filename=uploaded_file.name,
                                camera_id=camera_id
                            )
                        except Exception:
                            res = None

                        if res:
                            st.session_state["active_analyzed_video"] = uploaded_file.name
                            st.success(f"Analysis started on {uploaded_file.name}!")
                            st.rerun()
                        else:
                            st.error("Failed to upload video to backend. Ensure FastAPI backend is running.")
                else:
                    st.info(f"✅ Actively analyzing `{uploaded_file.name}`")


    # 1. Pipeline controls & Status bar
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1.5])


    status = client.get_session_status(camera_id)
    is_alive = status.get("is_alive", False) if status else False

    with col1:
        if not is_alive:
            if st.button("▶ Start Ingestion", type="primary", use_container_width=True):
                client.start_session(camera_id)
                st.rerun()
        else:
            if st.button("⏹ Stop Ingestion", type="secondary", use_container_width=True):
                client.stop_session(camera_id)
                st.rerun()

    with col2:
        st.metric(
            "Connection Status",
            "ONLINE" if is_alive else "STOPPED",
            delta="Streaming" if is_alive else "Standby",
            delta_color="normal" if is_alive else "off"
        )
    with col3:
        fps = status.get("fps", 0.0) if status else 0.0
        st.metric("Inference Rate", f"{fps:.1f} FPS")
    with col4:
        tracks = status.get("active_tracks_count", 0) if status else 0
        st.metric("Active Tracks", f"{tracks} persons")

    # 2. Main video player & overlay controls
    st.markdown("---")
    vid_col, ctrl_col = st.columns([3, 1])

    with ctrl_col:
        st.markdown("#### 🎛 Overlay Controls")
        st.caption("Level-of-Detail (LOD) Layer Toggles")
        lod_zones = st.checkbox("Workstation Polygons", value=True)
        lod_boxes = st.checkbox("Person Bounding Boxes", value=True)
        lod_feet = st.checkbox("Ground Footprints", value=True)
        lod_badges = st.checkbox("Salted Track Badges", value=True)
        lod_pills = st.checkbox("Activity State Pills", value=True)

        st.markdown("---")
        st.markdown("#### 🛡 Privacy Guard")
        st.info(
            "🔒 **Facial Recognition Ban Active**\n\n"
            "All faces are unmapped. Tracks use ephemeral hashes (`TRK-xxxx`) rotated daily."
        )

    with vid_col:
        stream_url = client.get_stream_url(camera_id)
        if is_alive:
            st.markdown(
                f'<div style="text-align:center; background-color:#111; border-radius:8px; padding:8px;">'
                f'<img src="{stream_url}" style="width:100%; max-height:540px; border-radius:6px; object-fit:contain;" />'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="height:360px; background-color:#1e293b; border-radius:8px; display:flex; '
                'align-items:center; justify-content:center; color:#94a3b8; flex-direction:column;">'
                '<span style="font-size:48px;">📹</span>'
                '<p style="margin-top:12px; font-size:16px;">Stream is currently paused or inactive.</p>'
                '<p style="font-size:13px; color:#64748b;">Click "Start Ingestion" above to activate the video perception pipeline.</p>'
                '</div>',
                unsafe_allow_html=True
            )

    # 3. Stream Health Metrics Footer
    st.markdown("---")
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        st.caption(f"**Camera Target:** `{camera_id}`")
    with h2:
        frames = status.get("total_frames_processed", 0) if status else 0
        st.caption(f"**Frames Ingested:** `{frames}`")
    with h3:
        dropped = status.get("dropped_frames_count", 0) if status else 0
        st.caption(f"**Dropped Frames:** `{dropped}`")
    with h4:
        cov = status.get("observation_coverage_pct", 0.0) if status else 0.0
        st.caption(f"**Observation Coverage:** `{cov:.1f}%`")
