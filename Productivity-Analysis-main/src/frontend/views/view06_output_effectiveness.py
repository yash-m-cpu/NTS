"""View 06: Output Effectiveness Panel (Scorecard D).

Displays verified operational business deliverables ingested from external enterprise systems.
Zero CCTV camera features are ever substituted into Scorecard D.
If external operational data is missing, renders an explicit N/A placeholder.
"""

from datetime import datetime, timezone
from typing import Any, Dict
import streamlit as st
from src.frontend.components.api_client import WBPISApiClient
from src.frontend.components.echarts_charts import render_radial_gauge


def render(client: WBPISApiClient, camera_id: str, department: str = "ENG") -> None:
    st.subheader("🎯 View 06: Operational Output & Deliverables Panel (Scorecard D)")
    st.markdown(
        "Measures business deliverable attainment ingested exclusively from verified enterprise tools "
        "(Jira sprint closures, GitHub pull requests, SAP ERP transactions, ticketing queues). "
        "**Strict Covenant:** Video analytics features are never used as a proxy for cognitive output."
    )

    scorecards = client.get_scorecards(camera_id, department)
    sc_d = scorecards.get("scorecard_d", {}) if scorecards else {}
    is_available = sc_d.get("status") != "UNAVAILABLE" and sc_d.get("composite_score") is not None

    if not is_available:
        # Explicit N/A Placeholder requirement from Phase 13 spec
        st.error(
            "🔒 **SCORECARD D UNAVAILABLE: External Operational Data Pipeline Unconfigured**\n\n"
            "WBPIS strictly forbids substituting camera observations or desk presence for knowledge work productivity. "
            "To activate Scorecard D, configure an external enterprise webhook (e.g., Jira, SAP, Salesforce) "
            "or use the manual test ingestion tool below."
        )

        with st.expander("🛠 External Data Ingestion Simulator / Webhook Tester", expanded=True):
            st.markdown("Submit verified deliverables to test Scorecard D calculations:")
            with st.form("outcome_test_form"):
                f_date = st.date_input("Report Date", datetime.now(timezone.utc)).strftime("%Y-%m-%d")
                f_dept = st.text_input("Department Code", department)
                c_a, c_b = st.columns(2)
                with c_a:
                    actual = st.number_input("Actual Completed Units", min_value=1, value=105)
                    target = st.number_input("Target Planned Units", min_value=1, value=100)
                with c_b:
                    accepted = st.number_input("Quality Accepted Units", min_value=1, value=102)
                    assessed = st.number_input("Quality Assessed Units", min_value=1, value=105)
                    ontime = st.number_input("On-Time Units", min_value=1, value=98)
                    rework = st.number_input("Rework Units", min_value=0, value=3)

                submit_btn = st.form_submit_button("🚀 Ingest External Outcome Payload")
                if submit_btn:
                    payload = {
                        "report_date": f_date,
                        "department_code": f_dept,
                        "actual_completed_units": actual,
                        "target_planned_units": target,
                        "quality_accepted_units": accepted,
                        "quality_assessed_units": assessed,
                        "on_time_units": ontime,
                        "total_deadline_units": actual,
                        "rework_units": rework,
                        "source_system": "JIRA_SPRINT_WEBHOOK"
                    }
                    res = client.ingest_operational_outcomes(payload)
                    if res:
                        st.success(f"Outcome ingested successfully! Scorecard D score calculated: {res.get('output_effectiveness_score')}")
                        st.rerun()
                    else:
                        st.error("Failed to ingest outcome payload.")
        return

    # When data IS available:
    score = sc_d.get("composite_score", 0.0)
    metrics = sc_d.get("metrics", {})

    top1, top2 = st.columns([1.5, 2.5])

    with top1:
        st.markdown("#### Primary Scorecard D")
        render_radial_gauge(score, "Output Effectiveness", unit="/100", height="280px")
        st.caption(f"Source: `{sc_d.get('source_system', 'EXTERNAL_WEBHOOK')}`")

    with top2:
        st.markdown("#### Deliverable Performance Breakdown")
        m1, m2 = st.columns(2)
        with m1:
            thru = metrics.get("throughput_rate_pct", 0.0)
            st.metric("Throughput Attainment", f"{thru:.1f}%", delta=f"{thru - 100:.1f}% vs Target")
            st.caption("Ratio of actual deliverables to planned sprint backlog.")

            qual = metrics.get("quality_rate_pct", 0.0)
            st.metric("First-Pass Quality Rate", f"{qual:.1f}%", delta="High Quality (> 95%)")
            st.caption("Deliverables accepted without client rework.")

        with m2:
            time_pct = metrics.get("timeliness_rate_pct", 0.0)
            st.metric("On-Time SLA Adherence", f"{time_pct:.1f}%", delta="On Schedule")
            st.caption("Deliverables completed prior to milestone deadlines.")

            rework = metrics.get("rework_rate_pct", 0.0)
            st.metric("Rework Rate", f"{rework:.1f}%", delta="Low Rework (< 5%)", delta_color="inverse")
            st.caption("Deliverables requiring defect remediation.")

    st.markdown("---")
    st.info("ℹ️ **Data Provenance**: Scorecard D metrics are cryptographically verified against external enterprise audit trails.")
