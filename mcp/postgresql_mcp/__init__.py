"""
postgresql_mcp — PostgreSQL MCP Server Package

Exposes structured read/write operations for the PostgreSQL state store.
This is the inter-phase data bus — every phase reads its inputs from here
and writes its outputs here.

Operations are grouped by phase. Import what you need:
    from mcp.postgresql_mcp.server import write_syllabus, check_syllabus_exists

Phase 1:  write_syllabus, check_syllabus_exists
Phase 2:  read_syllabus, write_refined_syllabus
Phase 3:  read_refined_syllabus, write_course_outcomes
Phase 4:  read_refined_syllabus, read_course_outcomes, write_lecture_plan
Phase 5a: read_lecture_plan, write_ppt_content
Phase 5b: read_lecture_plan, read_ppt_content
All:      log_phase_start, log_phase_complete
"""

from mcp.postgresql_mcp.server import (
    # Phase 1
    write_syllabus,
    check_syllabus_exists,
    # Phase 2
    read_syllabus,
    write_refined_syllabus,
    # Phase 3
    read_refined_syllabus,
    write_course_outcomes,
    # Phase 4
    read_course_outcomes,
    write_lecture_plan,
    # Phase 5a/5b
    read_lecture_plan,
    write_ppt_content,
    read_ppt_content,
    # Observability
    log_phase_start,
    log_phase_complete,
)

__all__ = [
    "write_syllabus",
    "check_syllabus_exists",
    "read_syllabus",
    "write_refined_syllabus",
    "read_refined_syllabus",
    "write_course_outcomes",
    "read_course_outcomes",
    "write_lecture_plan",
    "read_lecture_plan",
    "write_ppt_content",
    "read_ppt_content",
    "log_phase_start",
    "log_phase_complete",
]
