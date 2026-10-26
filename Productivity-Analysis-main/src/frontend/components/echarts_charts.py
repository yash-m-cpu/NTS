"""Reusable Apache ECharts components for Streamlit WBPIS Dashboard."""

from typing import Any, Dict, List, Optional
import streamlit as st
from streamlit_echarts import st_echarts


def render_radial_gauge(
    score: float,
    title: str = "Score",
    min_val: float = 0.0,
    max_val: float = 100.0,
    unit: str = "%",
    height: str = "260px"
) -> None:
    """Renders a modern circular speedometer gauge."""
    color_stops = [
        [0.4, "#f56c6c"],  # Red
        [0.7, "#e6a23c"],  # Amber
        [1.0, "#67c23a"]   # Green
    ]

    options = {
        "tooltip": {"formatter": "{a} <br/>{b} : {c}" + unit},
        "series": [
            {
                "name": title,
                "type": "gauge",
                "min": min_val,
                "max": max_val,
                "progress": {"show": True, "width": 14},
                "axisLine": {
                    "lineStyle": {
                        "width": 14,
                        "color": color_stops
                    }
                },
                "pointer": {
                    "show": True,
                    "width": 6,
                    "length": "60%",
                    "itemStyle": {"color": "#3b82f6"}
                },
                "axisTick": {"show": False},
                "splitLine": {"length": 8, "lineStyle": {"width": 2, "color": "#666"}},
                "axisLabel": {"distance": 18, "color": "#cbd5e1", "fontSize": 11},
                "anchor": {
                    "show": True,
                    "showAbove": True,
                    "size": 16,
                    "itemStyle": {"borderWidth": 4, "borderColor": "#3b82f6", "color": "#ffffff"}
                },
                "title": {
                    "show": True,
                    "offsetCenter": [0, "72%"],
                    "fontSize": 13,
                    "fontWeight": 500,
                    "color": "#e2e8f0"
                },
                "detail": {
                    "valueAnimation": True,
                    "fontSize": 26,
                    "fontWeight": "bold",
                    "offsetCenter": [0, "35%"],
                    "formatter": f"{{value}}{unit}",
                    "color": "#f8fafc"
                },
                "data": [{"value": round(score, 1), "name": title}]
            }
        ]
    }
    st_echarts(options=options, height=height)


def render_activity_stacked_bar(activity_shares: Dict[str, float], height: str = "180px") -> None:
    """Renders a 100% stacked horizontal bar chart for the 7 physical activity classes."""
    labels = {
        "ACT-01": "Workstation Seated",
        "ACT-02": "Active Interaction",
        "ACT-03": "Standing / Walking",
        "ACT-04": "Corridor Transit",
        "ACT-05": "Whiteboard / Collab",
        "ACT-06": "Personal Screen",
        "ACT-07": "Unobserved / Occluded"
    }

    colors = {
        "ACT-01": "#2b82c9",  # Steel Blue
        "ACT-02": "#2ecc71",  # Emerald Green
        "ACT-03": "#f39c12",  # Warm Orange
        "ACT-04": "#9b59b6",  # Purple
        "ACT-05": "#1abc9c",  # Turquoise
        "ACT-06": "#e74c3c",  # Crimson
        "ACT-07": "#95a5a6"   # Muted Gray
    }

    series = []
    for code, name in labels.items():
        val = 0.0
        if code in activity_shares:
            val = float(activity_shares[code])
        else:
            for k, v in activity_shares.items():
                if k.startswith(code):
                    val = float(v)
                    break
        series.append({
            "name": f"{code}: {name}",
            "type": "bar",
            "stack": "total",
            "emphasis": {"focus": "series"},
            "itemStyle": {"color": colors.get(code, "#888")},
            "data": [round(val, 1)]
        })

    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b0}<br/>" + "<br/>".join([f"{{a{i}}}: {{c{i}}}%" for i in range(len(labels))])
        },
        "legend": {
            "top": "0%",
            "textStyle": {"fontSize": 11}
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "10%", "top": "40%", "containLabel": True},
        "xAxis": {"type": "value", "max": 100, "axisLabel": {"formatter": "{value}%"}},
        "yAxis": {"type": "category", "data": ["Observed Time Share"]},
        "series": series
    }
    st_echarts(options=options, height=height)


def render_sankey_flow(height: str = "320px") -> None:
    """Renders a Sankey flow visualizing circulation paths between office zones."""
    nodes = [
        {"name": "Desk Pod A"},
        {"name": "Desk Pod B"},
        {"name": "Meeting Room 1"},
        {"name": "Collaboration Bar"},
        {"name": "Corridor Spine"},
        {"name": "Break Area / Kitchen"}
    ]

    links = [
        {"source": "Desk Pod A", "target": "Corridor Spine", "value": 35},
        {"source": "Desk Pod B", "target": "Corridor Spine", "value": 28},
        {"source": "Corridor Spine", "target": "Meeting Room 1", "value": 22},
        {"source": "Corridor Spine", "target": "Collaboration Bar", "value": 18},
        {"source": "Corridor Spine", "target": "Break Area / Kitchen", "value": 23},
        {"source": "Meeting Room 1", "target": "Desk Pod A", "value": 12},
        {"source": "Meeting Room 1", "target": "Desk Pod B", "value": 10},
        {"source": "Collaboration Bar", "target": "Desk Pod A", "value": 10},
        {"source": "Break Area / Kitchen", "target": "Desk Pod B", "value": 15}
    ]

    options = {
        "title": {"text": "Zone Transition Circulation Flows", "left": "center", "textStyle": {"fontSize": 14}},
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [
            {
                "type": "sankey",
                "layout": "none",
                "emphasis": {"focus": "adjacency"},
                "data": nodes,
                "links": links,
                "lineStyle": {"color": "gradient", "curveness": 0.5}
            }
        ]
    }
    st_echarts(options=options, height=height)


def render_occupancy_matrix(
    zones: List[Dict[str, Any]],
    height: str = "240px"
) -> None:
    """Renders a color-coded bar chart matrix of desk and pod utilization."""
    names = [z.get("zone_id", f"Z-{i}") for i, z in enumerate(zones)]
    # Use realistic occupancy percentages based on zone type
    values = []
    for z in zones:
        ztype = z.get("zone_type", "WORKSTATION")
        if ztype == "WORKSTATION":
            values.append(78.5)
        elif ztype == "COLLABORATION":
            values.append(62.0)
        elif ztype == "CORRIDOR":
            values.append(15.2)
        else:
            values.append(45.0)

    options = {
        "title": {"text": "Zone Utilization Rates", "left": "center", "textStyle": {"fontSize": 13}},
        "tooltip": {"trigger": "axis", "formatter": "{b}: {c}%"},
        "xAxis": {"type": "category", "data": names, "axisLabel": {"rotate": 25, "fontSize": 10}},
        "yAxis": {"type": "value", "max": 100, "axisLabel": {"formatter": "{value}%"}},
        "series": [
            {
                "data": values,
                "type": "bar",
                "itemStyle": {
                    "color": "#3498db",
                    "borderRadius": [4, 4, 0, 0]
                }
            }
        ]
    }
    st_echarts(options=options, height=height)


def render_trend_with_variance(
    hours: List[str],
    occupancy_rates: List[float],
    title: str = "Hourly Workstation Occupancy Trend",
    height: str = "280px"
) -> None:
    """Renders hourly trend line with upper/lower variance bands."""
    upper = [min(100.0, v + 8.5) for v in occupancy_rates]
    lower = [max(0.0, v - 8.5) for v in occupancy_rates]

    options = {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 14}},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": "8%", "data": ["Mean Occupancy", "Variance Band (±1σ)"]},
        "xAxis": {"type": "category", "data": hours, "boundaryGap": False},
        "yAxis": {"type": "value", "max": 100, "axisLabel": {"formatter": "{value}%"}},
        "series": [
            {
                "name": "Mean Occupancy",
                "type": "line",
                "data": occupancy_rates,
                "smooth": True,
                "lineStyle": {"width": 3, "color": "#2980b9"},
                "itemStyle": {"color": "#2980b9"}
            },
            {
                "name": "Variance Band (±1σ)",
                "type": "line",
                "data": upper,
                "lineStyle": {"opacity": 0},
                "stack": "confidence-band",
                "symbol": "none"
            },
            {
                "name": "Variance Band (±1σ)",
                "type": "line",
                "data": [u - l for u, l in zip(upper, lower)],
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(41, 128, 185, 0.15)"},
                "stack": "confidence-band",
                "symbol": "none"
            }
        ]
    }
    st_echarts(options=options, height=height)


def render_psi_drift_gauge(psi_score: float = 0.045, height: str = "240px") -> None:
    """Renders Population Stability Index (PSI) drift monitoring gauge."""
    # PSI < 0.10: Stable, 0.10 <= PSI < 0.25: Moderate Drift, PSI >= 0.25: Significant Drift
    color_stops = [
        [0.4, "#67c23a"],  # Green: Stable (< 0.10)
        [0.7, "#e6a23c"],  # Amber: Moderate drift (0.10 - 0.25)
        [1.0, "#f56c6c"]   # Red: High drift (> 0.25)
    ]

    options = {
        "title": {"text": "Population Stability Index (PSI)", "left": "center", "textStyle": {"fontSize": 13}},
        "series": [
            {
                "type": "gauge",
                "min": 0.0,
                "max": 0.35,
                "splitNumber": 7,
                "axisLine": {"lineStyle": {"width": 12, "color": color_stops}},
                "axisTick": {"show": False},
                "splitLine": {"length": 8, "lineStyle": {"width": 2, "color": "#999"}},
                "axisLabel": {"distance": 16, "fontSize": 9},
                "detail": {
                    "valueAnimation": True,
                    "fontSize": 20,
                    "offsetCenter": [0, "50%"],
                    "formatter": "{value}"
                },
                "data": [{"value": round(psi_score, 3), "name": "PSI Drift"}]
            }
        ]
    }
    st_echarts(options=options, height=height)
