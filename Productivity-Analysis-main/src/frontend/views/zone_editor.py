"""Spatial Zone Editor & Polygon Configuration.

Provides interactive creation, editing, and deletion of normalized spatial regions
of interest (ROIs). Solves BUG-02 by strictly enforcing floating-point coordinates in [0.0, 1.0].
"""

import json
from typing import Any, Dict, List
import pandas as pd
import streamlit as st
from src.frontend.components.api_client import WBPISApiClient


def render(client: WBPISApiClient, camera_id: str) -> None:
    st.subheader("📐 Interactive Spatial Zone & Polygon Editor")
    st.markdown(
        "Define and calibrate spatial regions of interest (workstations, corridors, collaboration spaces). "
        "Coordinates are stored as normalized floats `[0.0, 1.0]`, completely eliminating truncation errors (`BUG-02`)."
    )

    # 1. Existing Zones Table
    st.markdown("#### 🗺️ Currently Configured Zones")
    zones = client.get_zones(camera_id)

    if zones:
        table_rows = []
        for z in zones:
            coords = z.get("polygon_coords", [])
            coord_str = ", ".join([f"({p[0]:.2f}, {p[1]:.2f})" for p in coords[:4]])
            if len(coords) > 4:
                coord_str += "..."
            table_rows.append({
                "Zone ID": z.get("zone_id"),
                "Name": z.get("name"),
                "Type": z.get("zone_type"),
                "Capacity": z.get("capacity"),
                "Target Camera": z.get("camera_id"),
                "Vertices Count": len(coords),
                "Sample Coordinates [0.0, 1.0]": coord_str
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
    else:
        st.info("No spatial zones configured yet for this camera.")

    st.markdown("---")
    # 2. Add / Update Zone Form
    tab_add, tab_del = st.tabs(["➕ Add / Update Zone", "🗑️ Delete Zone"])

    with tab_add:
        st.markdown("##### Define Spatial Region Polygon")
        with st.form("create_zone_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                z_id = st.text_input("Zone ID (e.g. POD-01, DESK-03):", value="POD-03")
                z_name = st.text_input("Display Name:", value="Engineering Pod 3")
            with c2:
                z_type = st.selectbox(
                    "Zone Type:",
                    ["WORKSTATION", "COLLABORATION", "CORRIDOR", "FOCUS_ROOM", "SERVICE_RESOURCE"]
                )
                z_cap = st.number_input("Design Capacity (persons):", min_value=1, max_value=20, value=2)
            with c3:
                z_cam = st.text_input("Camera ID:", value=camera_id)

            st.markdown("##### Polygon Vertices (Normalized Float Coordinates in [0.0, 1.0])")
            st.caption("Provide at least 3 vertices (e.g. [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]]):")
            default_coords = "[\n  [0.10, 0.20],\n  [0.45, 0.20],\n  [0.45, 0.70],\n  [0.10, 0.70]\n]"
            coord_text = st.text_area("JSON Polygon Coordinates:", value=default_coords, height=120)

            submit_zone = st.form_submit_button("💾 Save Zone Definition")

            if submit_zone:
                try:
                    parsed_coords = json.loads(coord_text)
                    if not isinstance(parsed_coords, list) or len(parsed_coords) < 3:
                        st.error("Validation Error: Polygon must contain a list of at least 3 coordinate pairs.")
                    elif len(parsed_coords) > 12:
                        st.error("Validation Error: Maximum 12 vertices allowed per zone.")
                    else:
                        # Check bounds
                        valid = all(
                            isinstance(pt, list) and len(pt) == 2 and
                            0.0 <= pt[0] <= 1.0 and 0.0 <= pt[1] <= 1.0
                            for pt in parsed_coords
                        )
                        if not valid:
                            st.error("Coordinates must be floating point numbers within [0.0, 1.0].")
                        else:
                            payload = {
                                "zone_id": z_id.strip(),
                                "camera_id": z_cam.strip(),
                                "name": z_name.strip(),
                                "zone_type": z_type,
                                "capacity": z_cap,
                                "polygon_coords": parsed_coords
                            }
                            res = client.create_zone(payload)
                            if res:
                                st.success(f"Zone '{z_id}' saved successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to save zone definition with backend.")
                except json.JSONDecodeError as err:
                    st.error(f"Invalid JSON syntax in coordinates: {err}")

    with tab_del:
        st.markdown("##### Remove Spatial Zone")
        del_zone_opts = [z.get("zone_id") for z in zones] if zones else []
        if del_zone_opts:
            sel_del = st.selectbox("Select Zone to Remove:", del_zone_opts)
            if st.button("🗑️ Confirm Zone Deletion", type="primary"):
                ok = client.delete_zone(sel_del, camera_id)
                if ok:
                    st.success(f"Zone '{sel_del}' deleted successfully.")
                    st.rerun()
                else:
                    st.error("Failed to delete zone.")
        else:
            st.info("No zones available to delete.")
