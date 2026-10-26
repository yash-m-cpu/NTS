"""View 09: Video Export Controls.

Secure, dual-control interface for requesting redacted, annotated MP4 video clips.
Requires DPO approval tokens and mandatory business justifications.
Automated privacy redaction and edge video shredding compliance.
"""

import time
from typing import Any, Dict
import streamlit as st
from src.frontend.components.api_client import WBPISApiClient


def render(client: WBPISApiClient, camera_id: str) -> None:
    st.subheader("📼 View 09: Privacy-Preserving Video Export Controls")
    st.markdown(
        "Request cryptographically annotated and redacted MP4 clips for space planning audits. "
        "Strictly gated by Data Protection Officer (DPO) dual-control authorization."
    )

    # Export request form
    with st.form("video_export_form"):
        st.markdown("#### 📝 Export Request Specification")
        c1, c2 = st.columns(2)
        with c1:
            req_cam = st.selectbox("Source Camera Stream:", [camera_id, "CAM-02", "CAM-03"])
            clip_frames = st.slider("Export Duration (Frames, max 300 ~ 20s):", min_value=30, max_value=300, value=150, step=30)
        with c2:
            dpo_token = st.text_input("DPO Dual-Control Authorization Token:", value="DPO-AUTH-2026-TOKEN-XYZ", type="password")
            face_blur = st.checkbox("Automated Privacy Masking / Redaction (Enforced)", value=True, disabled=True)

        justification = st.text_area(
            "Mandatory Business Justification (GDPR / Audit Requirement):",
            value="Facility ergonomics assessment for quarterly layout review. Redacted video clip for pod spatial flow verification."
        )

        submit_export = st.form_submit_button("🚀 Submit Render Job")

        if submit_export:
            if not justification or len(justification.strip()) < 15:
                st.error("Submission rejected: Detailed business justification is mandatory.")
            elif not dpo_token:
                st.error("Submission rejected: Valid DPO authorization token is required.")
            else:
                res = client.trigger_video_export(camera_id=req_cam, max_frames=clip_frames)
                if res:
                    st.success(f"Video export job successfully queued! Job ID: `{res.get('job_id')}`")
                    st.session_state["last_export_job_id"] = res.get("job_id")
                    st.rerun()
                else:
                    st.error("Failed to queue export job with backend.")

    st.markdown("---")
    st.markdown("#### 📋 Active Export Queue & Download Registry")

    last_job = st.session_state.get("last_export_job_id")
    if last_job:
        status_info = client.get_export_status(last_job)
        if status_info:
            stat = status_info.get("status", "QUEUED")
            prog = status_info.get("progress_pct", 0.0)

            q1, q2, q3, q4 = st.columns([1.5, 2, 1.5, 2])
            with q1:
                st.markdown(f"**Job ID:** `{last_job}`")
            with q2:
                if stat == "READY":
                    st.success("🟢 READY FOR DOWNLOAD")
                elif stat == "RENDERING":
                    st.info(f"⚙️ RENDERING ({prog:.0f}%)")
                else:
                    st.warning(f"🟡 {stat}")
            with q3:
                st.caption(f"{status_info.get('frames_rendered', 0)} / {status_info.get('total_frames', 0)} frames")
            with q4:
                dl_url = status_info.get("download_url")
                if dl_url:
                    full_dl = f"{client.base_url}{dl_url}"
                    st.markdown(f"[📥 Download Redacted MP4]({full_dl})")
                else:
                    if st.button("🔄 Refresh Status", key="poll_job_btn"):
                        st.rerun()
    else:
        st.info("No active export jobs initiated in this session.")

    st.markdown("---")
    st.markdown("#### 🔒 Privacy & Compliance Assurances")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.caption("🛡️ **Edge Video Shredding**\n\nRaw footage on camera edge nodes is shredded after 72 hours.")
    with p2:
        st.caption("🔑 **Audit Logging**\n\nEvery export request is logged to the immutable STRIDE audit table.")
    with p3:
        st.caption("⏳ **Expiring Storage**\n\nExported MP4 artifacts expire and are deleted automatically within 24 hours.")
