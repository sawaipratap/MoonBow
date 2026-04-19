"""
Document Generation MCP Server
================================
Renders structured content produced by agents into actual files.
Two renderers: PPTX (Phase 5a) and Notes MD/PDF (Phase 5b).

Connects to:
  - python-pptx rendering service for PPTX files
  - markdown → PDF renderer (e.g. pandoc or WeasyPrint) for notes

Operations exposed to agents:
  - render_pptx(slide_data, course_code, lecture_number)   → str (MinIO path)  [Phase 5a]
  - render_notes(notes_data, course_code, lecture_number)  → dict (MD + PDF paths) [Phase 5b]

Why agents don't render files themselves:
  - Agents produce structured JSON content — rendering is deterministic formatting work
    that does not belong inside an LLM reasoning loop
  - Template changes (new slide design, new notes layout) only affect this server,
    not any agent node or graph
  - Keeps agent output schema stable regardless of rendered file format changes

Phases that use this server:
  - Phase 5a: render_pptx — after assembly node collects all slide content
  - Phase 5b: render_notes — after QA gate passes assembled notes
"""

import os
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PPTX_TEMPLATE_PATH: str = os.getenv("PPTX_TEMPLATE_PATH", "")
NOTES_TEMPLATE_PATH: str = os.getenv("NOTES_TEMPLATE_PATH", "")
OUTPUT_STAGING_DIR: str = os.getenv("DOC_GEN_STAGING_DIR", "/tmp/moonbow_docgen")

# After rendering, the file is handed off to filesystem_mcp.write_file()
# to store in MinIO. This server produces the bytes; filesystem_mcp stores them.


# ---------------------------------------------------------------------------
# Operation 1 — PPTX Renderer
# Used by: Phase 5a assembly node
# ---------------------------------------------------------------------------

def render_pptx(
    slide_data: list[dict],
    course_code: str,
    lecture_number: int,
    template_path: Optional[str] = None
) -> bytes:
    """
    Render a structured list of slide dicts into a PPTX file as raw bytes.

    Phase 5a's assembly node produces a structured JSON representation of
    all slides in a lecture. This function takes that structure and renders
    an actual presentation file using a predefined slide template.

    Args:
        slide_data: List of slide dicts from the assembly node. Each dict:
            {
                "slide_number": int,
                "title": str,
                "content_blocks": [
                    {"type": "bullet", "text": str},
                    {"type": "code", "language": str, "text": str},
                    {"type": "formula", "latex": str},
                    {"type": "visual_suggestion", "description": str}
                ],
                "speaker_notes": str,
                "narrative_role": str,   # "intro"|"concept"|"example"|"summary"
                "bloom_level": str       # e.g. "Apply"
            }
        course_code: E.g. "CSE2001" — used in file metadata
        lecture_number: 1-indexed lecture number — used in file naming
        template_path: Optional override for slide template. Uses
                       PPTX_TEMPLATE_PATH env var if not specified.

    Returns:
        Raw bytes of the rendered PPTX file.
        Caller is responsible for storing via filesystem_mcp.write_file().

    Raises:
        ValueError: if slide_data is empty
        FileNotFoundError: if template_path does not exist
        RuntimeError: if rendering fails
    """
    raise NotImplementedError(
        "render_pptx: Document generation not yet implemented.\n"
        "Implement using python-pptx when Phase 5a is being built."
    )


# ---------------------------------------------------------------------------
# Operation 2 — Notes Renderer
# Used by: Phase 5b QA gate (after pass)
# ---------------------------------------------------------------------------

def render_notes(
    notes_data: dict,
    course_code: str,
    lecture_number: int
) -> dict:
    """
    Render assembled notes content into both a Markdown file and a PDF.

    Phase 5b's notes assembler produces structured notes content after the
    QA gate passes. This function renders both a clean MD file (for version
    control and LMS upload) and a formatted PDF (for student distribution).

    Args:
        notes_data: Assembled notes dict from Phase 5b assembler:
            {
                "lecture_title": str,
                "lecture_number": int,
                "course_code": str,
                "subtopics": [
                    {
                        "subtopic_name": str,
                        "content_md": str,       # full markdown content for this subtopic
                        "examples": [str],
                        "practice_questions": [str],
                        "references": [str]
                    }
                ],
                "transitions": [str],            # bridging paragraphs between subtopics
                "assembled_md": str              # full assembled markdown document
            }
        course_code: E.g. "CSE2001"
        lecture_number: 1-indexed

    Returns:
        dict with:
        {
            "md_bytes": bytes,    # raw bytes of the rendered Markdown file
            "pdf_bytes": bytes    # raw bytes of the rendered PDF file
        }
        Caller stores both via filesystem_mcp.write_file() with appropriate content_types.

    Raises:
        ValueError: if notes_data is empty or assembled_md is missing
        RuntimeError: if PDF rendering fails (MD is always producible)
    """
    raise NotImplementedError(
        "render_notes: Document generation not yet implemented.\n"
        "Implement using pandoc CLI or WeasyPrint when Phase 5b is being built."
    )


# ---------------------------------------------------------------------------
# TODO: Real implementation notes
# ---------------------------------------------------------------------------
# PPTX rendering (render_pptx):
#   pip install python-pptx
#   from pptx import Presentation
#   from pptx.util import Inches, Pt
#   1. Load template: prs = Presentation(template_path or PPTX_TEMPLATE_PATH)
#   2. For each slide_dict in slide_data:
#      - prs.slides.add_slide(prs.slide_layouts[1])  # title+content layout
#      - Set title: slide.shapes.title.text = slide_dict["title"]
#      - Set content: iterate content_blocks, add text runs by type
#      - Set speaker notes: slide.notes_slide.notes_text_frame.text = speaker_notes
#   3. Save to BytesIO: buf = io.BytesIO(); prs.save(buf); return buf.getvalue()
#
# Notes PDF rendering (render_notes):
#   Option A: pandoc CLI
#     import subprocess, tempfile
#     with tempfile.NamedTemporaryFile(suffix=".md") as f:
#         f.write(notes_data["assembled_md"].encode())
#         result = subprocess.run(["pandoc", f.name, "-o", "/tmp/out.pdf", "--pdf-engine=xelatex"])
#     with open("/tmp/out.pdf", "rb") as f: pdf_bytes = f.read()
#   Option B: WeasyPrint (HTML → PDF)
#     from weasyprint import HTML
#     import markdown
#     html = markdown.markdown(notes_data["assembled_md"])
#     pdf_bytes = HTML(string=html).write_pdf()
#
# Both outputs (PPTX bytes, MD bytes, PDF bytes) are handed to filesystem_mcp.write_file()
# by the Phase 5a/5b output_writer nodes — this server only produces bytes.
