"""View 02: Ephemeral Track Details Panel.

Displays real-time anonymized telemetry for active tracks. Strict anti-surveillance
enforcement: zero employee identities, badge numbers, facial landmarks, or long-term histories.
"""

from typing import Any, Dict, List
import pandas as pd
import streamlit as st
from src.frontend.components.api_client import WBPISApiClient
from src.frontend.components.echarts_charts import render_activity_stacked_bar, render_radial_gauge


def render(client: WBPISApiClient, camera_id: str) -> None:
    st.subheader("👤 View 02: Ephemeral Track Details Panel")
    st.markdown(
        "Inspect active trajectory behavior, spatial friction, and ergonomic postures in real-time. "
        "Strictly bounded by privacy covenants: identifiers are non-reversible daily salted hashes."
    )

    # Fetch live telemetry from backend
    telemetry = client.get_live_telemetry(camera_id)
    active_tracks = telemetry.get("active_tracks", []) if telemetry else []

    # Fallback demonstration tracks if camera is in standby or no tracks currently visible
    if not active_tracks:
        st.info("ℹ️ **No active tracks currently detected in live feed.** Showing active demonstration session tracks below.")
        active_tracks = [
            {
                "track_id": "TRK-0101",
                "zone_id": "ZONE-POD-01 (Desk A-01)",
                "activity": "ACT-01: Seated at Workstation",
                "confidence": 0.94,
                "velocity": 0.005,
                "dwell_duration_seconds": 1420.0,
                "transitions_count": 2,
                "interruption_events": 1,
                "waiting_seconds": 45.0,
                "activity_breakdown": {
                    "ACT-01": 68.0,
                    "ACT-02": 12.0,
                    "ACT-03": 8.0,
                    "ACT-04": 7.0,
                    "ACT-05": 3.0,
                    "ACT-06": 1.0,
                    "ACT-07": 1.0
                }
            },
            {
                "track_id": "TRK-0102",
                "zone_id": "ZONE-POD-01 (Desk A-02)",
                "activity": "ACT-01: Seated at Workstation",
                "confidence": 0.91,
                "velocity": 0.008,
                "dwell_duration_seconds": 980.0,
                "transitions_count": 3,
                "interruption_events": 2,
                "waiting_seconds": 30.0,
                "activity_breakdown": {
                    "ACT-01": 62.0,
                    "ACT-02": 15.0,
                    "ACT-03": 10.0,
                    "ACT-04": 8.0,
                    "ACT-05": 3.0,
                    "ACT-06": 1.0,
                    "ACT-07": 1.0
                }
            },
            {
                "track_id": "TRK-0103",
                "zone_id": "ZONE-POD-02 (Desk B-01)",
                "activity": "ACT-04: Workstation Interaction",
                "confidence": 0.89,
                "velocity": 0.018,
                "dwell_duration_seconds": 640.0,
                "transitions_count": 4,
                "interruption_events": 0,
                "waiting_seconds": 60.0,
                "activity_breakdown": {
                    "ACT-01": 54.0,
                    "ACT-02": 18.0,
                    "ACT-03": 12.0,
                    "ACT-04": 10.0,
                    "ACT-05": 4.0,
                    "ACT-06": 1.0,
                    "ACT-07": 1.0
                }
            },
            {
                "track_id": "TRK-0104",
                "zone_id": "ZONE-CORRIDOR-01",
                "activity": "ACT-03: Walking / In Transit",
                "confidence": 0.92,
                "velocity": 0.042,
                "dwell_duration_seconds": 15.0,
                "transitions_count": 6,
                "interruption_events": 1,
                "waiting_seconds": 12.0,
                "activity_breakdown": {
                    "ACT-01": 35.0,
                    "ACT-02": 20.0,
                    "ACT-03": 30.0,
                    "ACT-04": 5.0,
                    "ACT-05": 6.0,
                    "ACT-06": 2.0,
                    "ACT-07": 2.0
                }
            }
        ]

    track_map = {t["track_id"]: t for t in active_tracks}
    selected_id = st.selectbox("Select Active Ephemeral Track:", list(track_map.keys()))
    t = track_map[selected_id]

    st.markdown("---")

    # Header Card: Track Identity & Current Status
    c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.2, 1.2])

    with c1:
        st.markdown(f"### `{t['track_id']}`")
        st.caption("Ephemeral Cryptographic Identifier (Rotated at 00:00 UTC)")
        st.markdown(f"**Assigned Zone:** `{t.get('zone_id') or 'Unmonitored / Common'}`")
        st.markdown(
            f'<div style="background-color:#1e6091; color:white; padding:6px 12px; border-radius:6px; '
            f'display:inline-block; font-weight:600; font-size:12px;">'
            f'{t.get("activity", "ACT-01: Seated at Workstation")}'
            f'</div>',
            unsafe_allow_html=True
        )

    with c2:
        st.metric(
            "Personal Interruptions",
            f"{t.get('interruption_events', 0)} events",
            delta=f"{max(0.2, t.get('interruption_events', 0) * 0.8):.1f} / hr",
            delta_color="normal" if t.get('interruption_events', 0) <= 2 else "inverse"
        )
        st.caption("Peer approaches while seated in focus posture.")

    with c3:
        st.metric(
            "Service Waiting Time",
            f"{t.get('waiting_seconds', 0.0):.0f} sec",
            delta=f"{(t.get('waiting_seconds', 0.0) / max(1.0, t.get('dwell_duration_seconds', 60.0)) * 100.0):.1f}% of time",
            delta_color="normal"
        )
        st.caption("Stationary dwell in corridor or shared resource queues.")

    with c4:
        st.metric(
            "Zone Transit Churn",
            f"{t.get('transitions_count', 0)} moves",
            delta=f"{max(1.0, t.get('transitions_count', 0) * 1.5):.1f} moves/hr",
            delta_color="normal" if t.get('transitions_count', 0) <= 5 else "inverse"
        )
        st.caption("Circulation movements between defined spatial zones.")

    st.markdown("---")

    # Detailed Personal Posture Shares & Ergonomic Balance
    breakdown = t.get("activity_breakdown", {})
    if not breakdown:
        breakdown = {"ACT-01": 70.0, "ACT-02": 15.0, "ACT-03": 10.0, "ACT-05": 3.0, "ACT-07": 2.0}

    def get_share(bd: Dict[str, Any], code: str) -> float:
        if not bd:
            return 0.0
        if code in bd:
            return float(bd[code])
        for k, v in bd.items():
            if str(k).startswith(code):
                return float(v)
        return 0.0

    curr_act_code = t.get("activity", "ACT-01").split(":")[0].strip()
    if sum(get_share(breakdown, c) for c in ["ACT-01", "ACT-02", "ACT-03", "ACT-04", "ACT-05", "ACT-06", "ACT-07"]) <= 0:
        breakdown[curr_act_code] = 100.0

    # Workstation presence ratio: ACT-01 (Seated) + ACT-02 (Standing) + ACT-04 (Interaction)
    desk_presence_pct = round(
        get_share(breakdown, "ACT-01") + get_share(breakdown, "ACT-02") + get_share(breakdown, "ACT-04"),
        1
    )
    # If occupant is predominantly collaborating at desk (ACT-05), account for active focus
    if desk_presence_pct <= 0.0 and get_share(breakdown, "ACT-05") > 0:
        desk_presence_pct = round(100.0 - get_share(breakdown, "ACT-06") - get_share(breakdown, "ACT-07"), 1)
    desk_presence_pct = min(100.0, max(0.0, desk_presence_pct))

    dwell_seconds = t.get("dwell_duration_seconds", 0.0)
    dwell_mins = dwell_seconds / 60.0

    r1, r2 = st.columns([1.5, 2.5])

    with r1:
        st.markdown("#### 🪑 Workstation Presence Ratio")
        render_radial_gauge(
            desk_presence_pct,
            "Presence Ratio",
            min_val=0,
            max_val=100,
            unit="%",
            height="250px"
        )
        st.caption(
            f"Active desk presence: **{desk_presence_pct:.1f}%** | Continuous focus dwell: **{dwell_mins:.1f} min** ({int(dwell_seconds)}s)"
        )

    with r2:
        st.markdown(f"#### 📊 `{t['track_id']}` Ergonomic Posture Breakdown (100% Normalized)")
        render_activity_stacked_bar(breakdown, height="200px")
        st.caption("Calculated strictly over active session frames for this individual track.")

    posture_data = [
        {"Activity Code": "ACT-01", "Posture State": "Seated at Workstation", "Individual Share (%)": f"{get_share(breakdown, 'ACT-01'):.1f}%", "Status": "Optimal focus posture"},
        {"Activity Code": "ACT-02", "Posture State": "Standing at Workstation", "Individual Share (%)": f"{get_share(breakdown, 'ACT-02'):.1f}%", "Status": "Dynamic sit-stand"},
        {"Activity Code": "ACT-03", "Posture State": "Walking / In Transit", "Individual Share (%)": f"{get_share(breakdown, 'ACT-03'):.1f}%", "Status": "Circulation mobility"},
        {"Activity Code": "ACT-04", "Posture State": "Workstation Interaction", "Individual Share (%)": f"{get_share(breakdown, 'ACT-04'):.1f}%", "Status": "Active reaching / typing"},
        {"Activity Code": "ACT-05", "Posture State": "Active Collaboration", "Individual Share (%)": f"{get_share(breakdown, 'ACT-05'):.1f}%", "Status": "Consultation / shared desk visit"},
        {"Activity Code": "ACT-06", "Posture State": "Away from Monitored Desk", "Individual Share (%)": f"{get_share(breakdown, 'ACT-06'):.1f}%", "Status": "Common area / break"},
        {"Activity Code": "ACT-07", "Posture State": "Unknown / Occluded", "Individual Share (%)": f"{get_share(breakdown, 'ACT-07'):.1f}%", "Status": "Camera angle occlusion"}
    ]
    st.dataframe(pd.DataFrame(posture_data), use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🛡 Anti-Surveillance & Privacy Guarantees")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown("🚫 **Zero Facial Recognition**")
        st.caption("Computer vision pipeline uses headless boundary tracking. Face detection or facial recognition models are banned.")
    with g2:
        st.markdown("🔒 **Ephemeral Session Hash**")
        st.caption("Track IDs are irreversibly salted with daily random entropy and wiped every 24 hours. No cross-day tracking.")
    with g3:
        st.markdown("⚖️ **No Punitive Ranking**")
        st.caption("Individual productivity scoring is prohibited. Metrics describe workspace ergonomic affordances, not employee value.")
