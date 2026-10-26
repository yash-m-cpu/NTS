"""Main Streamlit Application for WBPIS Analytics Dashboard.

Integrates all 10 operational views and the interactive spatial zone editor.
Strictly conforms to anti-surveillance covenants and Phase 13 frontend specifications.
"""

import os
import sys
from pathlib import Path

# Ensure project root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib
import streamlit as st

# Set page layout before any other Streamlit calls
st.set_page_config(
    page_title="WBPIS - Workplace Productivity & Workflow Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force reload of api_client to prevent stale module caching across hot-reloads
import src.frontend.components.api_client
importlib.reload(src.frontend.components.api_client)
from src.frontend.components.api_client import WBPISApiClient


from src.frontend.views import (

    view01_live_cctv,
    view02_track_details,
    view03_workflow_efficiency,
    view04_activity_distribution,
    view05_occupancy_presence,
    view06_output_effectiveness,
    view07_team_workspace,
    view08_historical_comparison,
    view09_video_export,
    view10_data_quality,
    zone_editor
)

# Initialize API client
backend_url = os.getenv("WBPIS_BACKEND_URL", "http://127.0.0.1:8000")
client = WBPISApiClient(backend_url)

# Custom CSS for polished interface
st.markdown(
    """
    <style>
    .main-title {
        font-size: 26px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .sub-title {
        font-size: 13px;
        color: #475569;
        margin-bottom: 16px;
    }
    .covenant-badge {
        background-color: #ecfdf5;
        border: 1px solid #10b981;
        color: #065f46;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar Configuration
with st.sidebar:
    st.markdown("### 🏢 WBPIS Intelligence")
    st.markdown('<div class="covenant-badge">🛡️ Anti-Surveillance Covenant Active</div>', unsafe_allow_html=True)

    # Health check indicator
    health = client.get_health()
    if health and health.get("status") == "HEALTHY":
        st.success(f"🟢 Backend Online (v{health.get('version', '1.0.0')})")
    else:
        st.warning("🟡 Backend Offline / Standby (Click Refresh)")
        if st.button("🔄 Check Backend Connection"):
            st.rerun()

    st.markdown("---")
    st.markdown("#### 🎯 Session Scoping")
    camera_id = st.selectbox("Active Camera Stream:", ["CAM-01", "CAM-02", "CAM-03"], index=0)
    department = st.selectbox("Target Department:", ["ENG", "PRODUCT", "OPERATIONS", "SALES"], index=0)

    with st.expander("📤 Upload Custom Video", expanded=True):
        sidebar_up = st.file_uploader("Upload video footage (.mp4, .avi):", type=["mp4", "avi", "mov", "mkv"], key="sb_video_up")
        if sidebar_up is not None:
            needs_upload = st.session_state.get("active_analyzed_video") != sidebar_up.name
            btn_clicked = st.button("🚀 Analyze Uploaded Video", use_container_width=True, type="primary", key="btn_sb_up")
            if needs_upload or btn_clicked:
                with st.spinner("Uploading video and binding to CCTV pipeline..."):
                    try:
                        res = client.upload_video(
                            file_bytes=sidebar_up.getvalue(),
                            filename=sidebar_up.name,
                            camera_id=camera_id
                        )
                    except Exception:
                        res = None

                    if res:
                        st.session_state["active_analyzed_video"] = sidebar_up.name
                        st.success(f"✅ Now analyzing: {sidebar_up.name}")
                        st.rerun()
                    else:
                        st.error("Upload failed. Ensure FastAPI backend is running.")
            else:
                st.success(f"🟢 Currently streaming: `{sidebar_up.name}`")


    st.markdown("---")
    st.markdown("#### 🧭 Operational Views")

    nav_selection = st.radio(
        "Select Dashboard View:",
        [
            "01. Live Annotated CCTV",
            "02. Ephemeral Track Details",
            "03. Workflow Efficiency (Scorecard A)",
            "04. Activity Distribution (Scorecard B)",
            "05. Occupancy & Presence (Scorecard C)",
            "06. Output Effectiveness (Scorecard D)",
            "07. Team & Workspace Overview",
            "08. Historical Trend Comparison",
            "09. Video Export Controls",
            "10. Data Quality & Model Health",
            "📐 Interactive Zone Editor"
        ],
        index=0
    )

    st.markdown("---")
    st.caption("CCTV Workplace Productivity & Workflow Intelligence System | Phase 13")

# Main Header
st.markdown('<div class="main-title">Workplace Productivity & Workflow Intelligence System (WBPIS)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Spatial ergonomics, workflow bottleneck diagnostics, and privacy-preserving architectural analytics.</div>', unsafe_allow_html=True)

# View Dispatcher
if nav_selection.startswith("01."):
    view01_live_cctv.render(client, camera_id)
elif nav_selection.startswith("02."):
    view02_track_details.render(client, camera_id)
elif nav_selection.startswith("03."):
    view03_workflow_efficiency.render(client, camera_id, department)
elif nav_selection.startswith("04."):
    view04_activity_distribution.render(client, camera_id, department)
elif nav_selection.startswith("05."):
    view05_occupancy_presence.render(client, camera_id, department)
elif nav_selection.startswith("06."):
    view06_output_effectiveness.render(client, camera_id, department)
elif nav_selection.startswith("07."):
    view07_team_workspace.render(client, camera_id, department)
elif nav_selection.startswith("08."):
    view08_historical_comparison.render(client, camera_id, department)
elif nav_selection.startswith("09."):
    view09_video_export.render(client, camera_id)
elif nav_selection.startswith("10."):
    view10_data_quality.render(client, camera_id)
elif nav_selection.startswith("📐"):
    zone_editor.render(client, camera_id)
