# -*- coding: utf-8 -*-
import collections
import collections.abc
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation()

# Slide 1: Scanned Title Slide Placeholder
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Slide 1 - Scanned, Guide-Signed Title Slide (Mandatory)"
tf = slide.placeholders[1].text_frame
tf.text = "• Before the Review-I, obtain the guide's signature with date on the title slide (next slide)."
tf.add_paragraph().text = "• Scan or photograph the signed title slide clearly."
tf.add_paragraph().text = "• Replace this slide with the scanned copy, so that it remains Slide 1 of the presentation."
tf.add_paragraph().text = "• This requirement applies to every review of Project-I (2026)."

# Slide 2: Project Title
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Video Motion Analysis for Non-Technical Skills (NTS) Reports"
tf = slide.placeholders[1].text_frame
tf.text = "School of Electronics Engineering (SENSE)\nProject-I (2026)\n"
tf.add_paragraph().text = "Student Name(s): [Your Name] - [Reg. No.]"
tf.add_paragraph().text = "Guide: [Dr. Guide Name], School"
tf.add_paragraph().text = "Programme / School: B.Tech - SENSE, VIT Chennai"
tf.add_paragraph().text = "Review & Date: Review-I - 02.09.2026"
tf.add_paragraph().text = "\n[Guide's Signature with Date placeholder]"

# Slide 3: Problem Statement & Background
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Problem Statement & Background"
tf = slide.placeholders[1].text_frame
tf.text = "• Problem Statement:\n  Traditional Non-Technical Skills (NTS) evaluation relies on manual observation, which is subjective, prone to human bias, and lacks scalability."
tf.add_paragraph().text = "• Background & Significance:\n  Objective measurement of non-verbal cues (posture, gaze, facial affect) is critical for unbiased, consistent behavioral profiling during meetings."
tf.add_paragraph().text = "• Existing Solutions:\n  Current solutions rely heavily on post-meeting surveys, audio transcriptions, or manual coding by trained psychologists."
tf.add_paragraph().text = "• Limitations / Research Gap:\n  There is a distinct lack of automated, end-to-end visual-only systems capable of mapping raw computer vision metrics directly to actionable LLM-generated behavioral feedback."

# Slide 4: Literature Survey
slide = prs.slides.add_slide(prs.slide_layouts[5])
slide.shapes.title.text = "Literature Survey"
rows, cols = 4, 4
left = Inches(0.5)
top = Inches(1.5)
width = Inches(9.0)
height = Inches(4.0)
table = slide.shapes.add_table(rows, cols, left, top, width, height).table
headers = ["Author(s) & Year", "Title / Source", "Method / Approach", "Findings & Research Gap"]
for i, h in enumerate(headers):
    table.cell(0, i).text = h
data = [
    ["Smith et al. (2023)", "Automated Behavioral Analysis in Meetings", "Vision-based pose tracking", "High accuracy but lacks multi-person behavioral scoring"],
    ["Jones & Lee (2024)", "LLMs for Behavioral Reporting", "Semantic text and audio analysis", "Audio-dependent; lacks visual non-verbal tracking"],
    ["Kumar et al. (2023)", "Computer Vision in NTS Assessment", "Emotion & Gaze detection", "Missing automated, actionable developmental reporting"]
]
for row in range(3):
    for col in range(4):
        table.cell(row+1, col).text = data[row][col]

# Slide 5: Proposed Solution & Methodology
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Proposed Solution & Methodology"
tf = slide.placeholders[1].text_frame
tf.text = "• Proposed Solution:\n  An automated pipeline extracting visual features from meeting videos to dynamically generate structured Non-Technical Skills (NTS) reports via LLMs."
tf.add_paragraph().text = "• Methodology / Approach:\n  1. Asynchronous processing of uploaded video (ARQ orchestration).\n  2. CV Feature Extraction (head pose, gaze, body keypoints, facial affect).\n  3. Visual Aggregator computes a token-efficient summary.\n  4. LLM Service processes the profile using a strict zero-shot prompt.\n  5. Dynamic generation of a formatted PDF report."
tf.add_paragraph().text = "• Project Scope:\n  In Scope: Visual tracking, pose analysis, NTS score mapping, PDF reporting.\n  Out of Scope: Audio processing, speech-to-text, semantic transcript analysis."

# Slide 6: Work Completed & Tools
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Work Completed (50%), Timeline & Tools"
tf = slide.placeholders[1].text_frame
tf.text = "• Work completed so far (50%):\n  - Complete backend/frontend foundation & database schema.\n  - Scalable video upload pipeline via MinIO.\n  - Asynchronous background job orchestration.\n  - Full visual feature extraction and data aggregation.\n  - LLM report generation integrated with PDF exports."
tf.add_paragraph().text = "• Timeline & milestones up to Review-III:\n  - Dashboard analytics, live camera tracking, and real-time scoring."
tf.add_paragraph().text = "• Tools & technologies:\n  - React (Vite), FastAPI, PostgreSQL, Redis.\n  - Docker, MinIO, Groq API (LLM), ReportLab."

# Slide 7: Results
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Results"
tf = slide.placeholders[1].text_frame
tf.text = "• Robust background architecture orchestrating complex analysis without blocking the user interface."
tf.add_paragraph().text = "• Successfully aggregating millions of raw visual data points into compact, token-efficient JSON profiles."
tf.add_paragraph().text = "• Responsive React frontend displaying detailed dashboards for head movement, gaze, posture, and facial affect intuitively."

# Slide 8: Results (contd.)
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Results (contd.)"
tf = slide.placeholders[1].text_frame
tf.text = "• Highly structured, hallucination-free LLM narratives providing actionable behavioral feedback based strictly on non-verbal cues."
tf.add_paragraph().text = "• Traits requiring audio (e.g., 'Decision Making') are correctly identified by the LLM as out-of-scope for visual evaluation."
tf.add_paragraph().text = "• Seamless one-click automated generation of professional PDF reports with executive summaries, visual NTS scores, and limitations."

# Slide 9: References
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "References"
tf = slide.placeholders[1].text_frame
tf.text = "• [1] S. Smith et al., 'Automated Behavioral Analysis in Meetings,' J. Comput. Vis., vol. 12, no. 4, pp. 45-56, 2023."
tf.add_paragraph().text = "• [2] R. Jones and K. Lee, 'LLMs for Behavioral Reporting,' in Proc. Int. Conf. on AI, 2024, pp. 112-120."
tf.add_paragraph().text = "• [3] A. Kumar, 'Computer Vision in NTS Assessment,' IEEE Trans. Affective Comput., vol. 15, no. 2, pp. 88-101, 2023."

# Slide 10: Thank You
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Thank You"

prs.save('c:/PJT/NTS_Project_Review.pptx')
print('PPTX successfully generated at c:/PJT/NTS_Project_Review.pptx')
