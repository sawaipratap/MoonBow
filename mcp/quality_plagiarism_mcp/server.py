"""
Quality / Plagiarism MCP Server
================================
Performs content quality and originality checks on generated notes.
Used as a TOOL (always called) by Phase 5b's QA gate node.

Connects to:
  - Internal quality scoring service (LLM-based coverage checker)
  - External originality/plagiarism API (e.g. Copyleaks, PlagScan, or custom)

Operations exposed to agents:
  - check_quality(notes_content, lecture_plan)     → dict  [Phase 5b QA gate]
  - check_originality(text_block)                  → dict  [Phase 5b QA gate]

Why the QA gate calls both:
  - Quality check: verifies the assembled notes actually cover all subtopics
    from the lecture plan — no subtopic should be missing or too shallow.
  - Originality check: verifies the generated content is not reproducing
    source material verbatim. LLMs can sometimes output memorised text.

Phase 5b's QA gate behaviour on failures:
  - Quality fail on a subtopic → regenerate ONLY that subtopic (not the whole lecture)
  - Plagiarism fail → flag the affected section for human review (not auto-regeneration)

Phases that use this server:
  - Phase 5b: QA gate node (always called, not optional)
"""

import os
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QUALITY_CHECK_THRESHOLD: float = float(os.getenv("QUALITY_THRESHOLD", "0.80"))
ORIGINALITY_THRESHOLD: float = float(os.getenv("ORIGINALITY_THRESHOLD", "0.85"))

PLAGIARISM_API_URL: str = os.getenv("PLAGIARISM_API_URL", "")
PLAGIARISM_API_KEY: str = os.getenv("PLAGIARISM_API_KEY", "")


# ---------------------------------------------------------------------------
# Operation 1 — Quality Check
# Used by: Phase 5b QA gate node (always called)
# ---------------------------------------------------------------------------

def check_quality(
    assembled_notes: dict,
    lecture_plan_entry: dict
) -> dict:
    """
    Verify that the assembled lecture notes adequately cover all subtopics
    listed in the lecture plan for that lecture.

    This is a coverage check — it verifies completeness, not correctness.
    Correctness is the responsibility of the notes agents themselves.

    Args:
        assembled_notes: The AssembledNotes dict from Phase 5b assembler:
            {
                "lecture_number": int,
                "subtopics": [
                    {
                        "subtopic_name": str,
                        "content_md": str,
                        "word_count": int
                    }
                ],
                "assembled_md": str
            }
        lecture_plan_entry: The lecture's entry from the LecturePlan array:
            {
                "lecture_number": int,
                "title": str,
                "subtopics": [str],          # expected subtopic names
                "duration_minutes": int,
                "cos_addressed": [str],
                "bloom_levels_targeted": [str]
            }

    Returns:
        dict with:
        {
            "pass": bool,
            "quality_score": float,          # 0.0–1.0 overall
            "subtopic_scores": {
                "subtopic_name": {
                    "covered": bool,
                    "depth_score": float,    # 0.0–1.0
                    "word_count": int,
                    "below_threshold": bool
                }
            },
            "failing_subtopics": [str],      # names of subtopics that need regeneration
            "missing_subtopics": [str],      # subtopics in plan but completely absent in notes
            "overall_feedback": str
        }

    Raises:
        ValueError: if assembled_notes or lecture_plan_entry is empty
        ConnectionError: if the quality check service is unreachable
    """
    raise NotImplementedError(
        "check_quality: Quality check service not yet implemented.\n"
        "In mock mode, MockQualityChecker returns pass=True with full scores.\n"
        "Implement using an LLM call or structured scoring logic."
    )


# ---------------------------------------------------------------------------
# Operation 2 — Originality Check
# Used by: Phase 5b QA gate node (always called)
# ---------------------------------------------------------------------------

def check_originality(
    text_block: str,
    course_code: str,
    lecture_number: int
) -> dict:
    """
    Check a block of generated text for originality — verifies it is not
    reproducing copyrighted source material verbatim.

    Phase 5b calls this after the notes assembler produces the full lecture
    notes. If sections fail, they are flagged for human review — failed
    originality does NOT trigger automatic regeneration (unlike quality fails).

    Args:
        text_block: The full assembled notes markdown text for the lecture.
                    Passed as a single block to minimise API calls.
        course_code: For audit logging — e.g. "CSE2001"
        lecture_number: For audit logging — 1-indexed

    Returns:
        dict with:
        {
            "pass": bool,
            "originality_score": float,      # 0.0–1.0. 1.0 = fully original
            "flagged_sections": [
                {
                    "text_excerpt": str,     # first 100 chars of flagged passage
                    "similarity_pct": float, # e.g. 0.92 = 92% match with source
                    "source_reference": str  # where the match was found, if available
                }
            ],
            "requires_human_review": bool,
            "audit_id": str                  # ID for tracking this check in audit logs
        }

    Raises:
        ValueError: if text_block is empty
        ConnectionError: if the plagiarism API is unreachable.
                         On ConnectionError, QA gate logs a warning and marks
                         originality as "skipped" — does not block notes output.
    """
    raise NotImplementedError(
        "check_originality: Plagiarism API not yet connected.\n"
        "Set PLAGIARISM_API_URL and PLAGIARISM_API_KEY in .env when ready.\n"
        "In mock mode, MockQualityChecker returns pass=True, originality_score=1.0."
    )


# ---------------------------------------------------------------------------
# TODO: Real implementation notes
# ---------------------------------------------------------------------------
# check_quality (coverage check):
#   Option A: LLM-based scoring
#     - For each expected subtopic in lecture_plan_entry["subtopics"]:
#       - Search assembled_notes["assembled_md"] for the subtopic content
#       - Use an LLM call with sentence "Does this notes section adequately
#         cover {subtopic}? Score 0-1." with the relevant section as context
#       - Aggregate scores across subtopics
#     - Threshold: QUALITY_CHECK_THRESHOLD (default 0.80)
#   Option B: Heuristic (faster, no LLM call):
#     - Check each subtopic name appears in assembled_md (presence check)
#     - Check word count per subtopic section >= minimum (e.g. 300 words for UG)
#     - Flag any subtopic with word_count < threshold or not mentioned
#
# check_originality (plagiarism check):
#   Option A: Copyleaks API
#     import requests
#     headers = {"Authorization": f"Bearer {PLAGIARISM_API_KEY}"}
#     response = requests.post(
#         f"{PLAGIARISM_API_URL}/v1/education/check",
#         json={"text": text_block},
#         headers=headers
#     )
#     result = response.json()
#     originality_score = result["statistics"]["identical"]["percentageAggregated"]
#   Option B: Custom fingerprinting
#     - Split text into sentences
#     - Hash sentences and compare against a local database of known text
#     - Fast but limited coverage
#
# MockQualityChecker for mock mode (to be placed in phase5b/mocks/):
#   class MockQualityChecker:
#       def check_quality(self, assembled_notes, lecture_plan_entry):
#           return {"pass": True, "quality_score": 1.0, "failing_subtopics": [],
#                   "missing_subtopics": [], "subtopic_scores": {}, "overall_feedback": "Mock pass"}
#       def check_originality(self, text_block, course_code, lecture_number):
#           return {"pass": True, "originality_score": 1.0, "flagged_sections": [],
#                   "requires_human_review": False, "audit_id": "mock_audit_001"}
