"""
pdf_generator.py
Generates a PDF report from structured report JSON using reportlab.
Uploads the PDF to MinIO and returns (bucket, key).
No CV re-inference. No LLM calls.
"""
import io
import logging
import uuid
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ---------- Style helpers ----------

def _styles():
    base = getSampleStyleSheet()
    custom = {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"],
            fontSize=22, spaceAfter=6, textColor=colors.HexColor("#1a237e"),
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            fontSize=14, spaceBefore=14, spaceAfter=4,
            textColor=colors.HexColor("#283593"), borderPad=2,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontSize=11, spaceBefore=8, spaceAfter=2,
            textColor=colors.HexColor("#37474f"),
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=9, leading=13, spaceAfter=4,
            alignment=TA_JUSTIFY,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"],
            fontSize=9, leading=13, spaceAfter=2,
            leftIndent=12, bulletIndent=0,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["Normal"],
            fontSize=8, textColor=colors.grey,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["Normal"],
            fontSize=8, textColor=colors.HexColor("#37474f"),
            fontName="Helvetica-Bold",
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer", parent=base["Normal"],
            fontSize=7.5, textColor=colors.grey, leading=11,
            borderPad=4, backColor=colors.HexColor("#f5f5f5"),
            alignment=TA_JUSTIFY,
        ),
    }
    return custom


def _hr():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdbdbd"), spaceAfter=6)


def _section_header(text: str, styles: dict) -> list:
    return [_hr(), Paragraph(text, styles["h1"])]


def _bullet_list(items: list[str], styles: dict) -> list:
    return [Paragraph(f"• {item}", styles["bullet"]) for item in items if item]


# ---------- NTS Score Table ----------

def _nts_table(nts_profile: dict) -> Table:
    DIMENSION_LABELS = {
        "communication": "Communication (Non-verbal)",
        "teamwork": "Teamwork (Visual Indicators)",
        "leadership": "Leadership (Visual Indicators)",
        "influence": "Influence (Visual Indicators)",
        "resilience_consistency": "Resilience-related Consistency",
        "decision_making": "Decision-Making",
    }
    rows = [["Dimension", "Score", "Confidence", "Status"]]
    for key, label in DIMENSION_LABELS.items():
        dim = nts_profile.get(key, {})
        if key == "decision_making":
            rows.append([label, "—", "—", "Not Assessed (Visual-Only)"])
        else:
            score = dim.get("score")
            conf = dim.get("confidence")
            score_str = f"{score}/100" if score is not None else "Insufficient data"
            conf_str = f"{round(float(conf) * 100)}%" if conf is not None else "—"
            status = "Assessed" if score is not None else "Pending"
            rows.append([label, score_str, conf_str, status])

    t = Table(rows, colWidths=[7 * cm, 3 * cm, 3 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#283593")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e8eaf6")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bdbdbd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ---------- Data Quality Table ----------

def _quality_table(report_input: dict) -> Table:
    coverage = report_input.get("coverage", 0)
    det_conf = report_input.get("detection_confidence")
    quality = report_input.get("data_quality", "unknown")
    missing = report_input.get("missing_features", [])
    duration = report_input.get("duration_seconds", 0)
    detections = report_input.get("total_detections", 0)

    rows = [
        ["Metric", "Value"],
        ["Analysis Duration", f"{round(duration / 60, 1)} min ({duration}s)"],
        ["Feature Coverage", f"{round(coverage * 100)}%"],
        ["Detection Confidence", f"{round(det_conf * 100)}%" if det_conf else "N/A"],
        ["Total Detections", str(detections)],
        ["Data Quality", quality.upper()],
        ["Missing Features", ", ".join(missing) if missing else "None"],
    ]

    t = Table(rows, colWidths=[6 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bdbdbd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ---------- Main PDF Builder ----------

def build_pdf_bytes(report_json: dict, report_input: dict, meeting_id: str) -> bytes:
    """Build PDF in memory and return bytes. Never calls LLM or CV."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="NTS Visual Behavioral Report",
    )
    styles = _styles()
    story = []

    track_label = report_input.get("track_label", report_json.get("participant_id", "Unknown"))

    # ---------- Cover ----------
    story.append(Paragraph("NTS Visual Behavioral Report", styles["title"]))
    story.append(Paragraph(f"Participant: <b>{track_label}</b>", styles["h2"]))
    story.append(Paragraph(f"Meeting ID: {meeting_id}", styles["meta"]))
    story.append(Paragraph(
        f"Analysis Duration: {round(report_input.get('duration_seconds', 0) / 60, 1)} min  |  "
        f"Feature Coverage: {round(report_input.get('coverage', 0) * 100)}%  |  "
        f"Data Quality: {report_input.get('data_quality', 'N/A').upper()}",
        styles["meta"]
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "⚠ This report is derived from observable video-based visual features only. "
        "It is NOT a psychological assessment, personality profile, or definitive evaluation.",
        styles["disclaimer"]
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ---------- Executive Summary ----------
    story.extend(_section_header("Executive Summary", styles))
    exec_summary = report_json.get("executive_summary", "No summary generated.")
    for para in exec_summary.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["body"]))
    story.append(Spacer(1, 0.2 * cm))

    # ---------- Visual Profile ----------
    story.extend(_section_header("Visual Profile", styles))
    vp = report_json.get("visual_profile", {})
    profile_keys = [
        ("head_movement", "Head Movement"),
        ("gaze", "Gaze"),
        ("posture", "Posture"),
        ("hands_gestures", "Hands & Gestures"),
        ("facial_affect", "Facial Affect"),
    ]
    for key, label in profile_keys:
        val = vp.get(key)
        if val:
            story.append(Paragraph(f"<b>{label}:</b> {val}", styles["body"]))
    story.append(Spacer(1, 0.2 * cm))

    # ---------- NTS Visual Profile ----------
    story.extend(_section_header("NTS Visual Profile", styles))
    story.append(Paragraph(
        "Scores represent visual behavioral proxies only. They are not definitive NTS assessments.",
        styles["meta"]
    ))
    story.append(Spacer(1, 0.2 * cm))
    nts = report_json.get("nts_visual_profile", {})
    story.append(_nts_table(nts))

    # Evidence per dimension
    for key in ["communication", "teamwork", "leadership", "influence", "resilience_consistency"]:
        dim = nts.get(key, {})
        evidence = dim.get("evidence", [])
        if evidence:
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(f"<b>{key.replace('_', ' ').title()} — Evidence:</b>", styles["label"]))
            story.extend(_bullet_list(evidence, styles))

    story.append(Spacer(1, 0.3 * cm))

    # ---------- Strengths ----------
    story.extend(_section_header("Key Strengths", styles))
    story.extend(_bullet_list(report_json.get("strengths", []), styles))
    story.append(Spacer(1, 0.2 * cm))

    # ---------- Development Areas ----------
    story.extend(_section_header("Areas for Development", styles))
    story.extend(_bullet_list(report_json.get("development_areas", []), styles))
    story.append(Spacer(1, 0.2 * cm))

    # ---------- Recommendations ----------
    story.extend(_section_header("Recommended Actions", styles))
    story.extend(_bullet_list(report_json.get("recommendations", []), styles))
    story.append(Spacer(1, 0.2 * cm))

    # ---------- Detailed Summary ----------
    story.extend(_section_header("Detailed Individual Summary", styles))
    detailed = report_json.get("detailed_summary", "")
    for para in detailed.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["body"]))
    story.append(Spacer(1, 0.3 * cm))

    # ---------- Data Quality ----------
    story.extend(_section_header("Data Quality & Coverage", styles))
    story.append(_quality_table(report_input))
    story.append(Spacer(1, 0.2 * cm))

    # ---------- Limitations ----------
    story.extend(_section_header("Limitations & Disclaimer", styles))
    limitations = report_json.get("limitations", [])
    if limitations:
        story.extend(_bullet_list(limitations, styles))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "This report is generated from observable video-based visual features (head orientation, "
        "gaze direction, body keypoints, hand visibility, and facial affect patterns). "
        "It does NOT incorporate speech, audio, semantic content, or psychological assessment. "
        "NTS scores are derived visual proxies and should be interpreted alongside other evaluations. "
        "Detection confidence reflects the computer vision model's detection quality, not the participant's "
        "personal confidence or any psychological trait.",
        styles["disclaimer"]
    ))

    doc.build(story)
    return buffer.getvalue()


async def generate_and_upload_pdf(
    report_json: dict,
    report_input: dict,
    meeting_id: str,
    track_id: str,
) -> tuple[str, str]:
    """Generate PDF bytes and upload to MinIO. Returns (bucket, key)."""
    from app.services.storage_service import get_s3_client
    from app.core.config import settings

    pdf_bytes = build_pdf_bytes(report_json, report_input, meeting_id)
    bucket = settings.S3_BUCKET_NAME
    key = f"reports/{meeting_id}/{track_id}/nts_visual_report.pdf"

    async with get_s3_client() as s3:
        await s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )

    logger.info("PDF uploaded to s3://%s/%s", bucket, key)
    return bucket, key
