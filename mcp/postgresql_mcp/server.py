"""
PostgreSQL MCP Server
=====================
Provides a standardised read/write interface to the PostgreSQL database
that serves as the structured state store for the entire pipeline.

Connects to: PostgreSQL (schema defined below)

Operations exposed to agents:
  Phase 1:
    - write_syllabus(syllabus, course_code, phase_status, iteration_count) → record_id
    - check_syllabus_exists(course_code)                                   → bool

  Phase 2:
    - read_syllabus(course_code)                                           → dict
    - write_refined_syllabus(syllabus, course_code, evaluation_results)    → record_id

  Phase 3:
    - read_refined_syllabus(course_code)                                   → dict
    - write_course_outcomes(cos, course_code)                              → record_id

  Phase 4:
    - read_refined_syllabus(course_code)                                   → dict
    - read_course_outcomes(course_code)                                    → dict
    - write_lecture_plan(lecture_plan, course_code)                        → record_id

  Phase 5a:
    - read_lecture_plan(course_code)                                       → list[dict]
    - write_ppt_content(ppt_content, course_code, lecture_number)          → record_id

  Phase 5b:
    - read_lecture_plan(course_code)                                       → list[dict]
    - read_ppt_content(course_code, lecture_number)                        → dict

Why MCP and not direct DB access:
  - Enforces the read/write interface contract per phase
  - No agent has raw SQL access — prevents accidental cross-phase data access
  - Swapping DB or schema changes only affects this one server, not any graph code

Database Schema Overview:
  - syllabuses        (course_code PK, syllabus JSONB, phase_status, iteration_count, created_at)
  - refined_syllabuses(course_code PK, syllabus JSONB, evaluation_results JSONB, created_at)
  - course_outcomes   (course_code PK, outcomes JSONB, created_at)
  - lecture_plans     (course_code PK, plan JSONB, created_at)
  - ppt_content       (course_code, lecture_number, content JSONB, created_at)
  - pipeline_runs     (run_id PK, course_code, phase, status, started_at, completed_at)

All tables use JSONB for structured content. Schema DDL is in db/schema.sql (to be created).
"""

import os
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME: str = os.getenv("POSTGRES_DB", "moonbow")
DB_USER: str = os.getenv("POSTGRES_USER", "moonbow_user")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
DB_POOL_SIZE: int = int(os.getenv("POSTGRES_POOL_SIZE", "5"))


# ---------------------------------------------------------------------------
# Phase 1 Operations
# ---------------------------------------------------------------------------

def write_syllabus(
    syllabus: dict,
    course_code: str,
    phase_status: str,
    iteration_count: int
) -> str:
    """
    Write the Phase 1 output (SyllabusDraft) to the syllabuses table.

    Args:
        syllabus: SyllabusDraft as a dict (from model.model_dump())
        course_code: Unique course identifier (primary key in syllabuses table)
        phase_status: "passed" | "force_passed"
        iteration_count: How many expander-critic cycles were used

    Returns:
        record_id: The course_code, confirming successful write (or DB-generated UUID).

    Raises:
        ConnectionError: if DB connection fails
        ValueError: if syllabus dict fails JSONB schema validation
    """
    raise NotImplementedError(
        "write_syllabus: PostgreSQL not yet connected. "
        "Use MockDBWriter via dependencies.py in mock mode."
    )


def check_syllabus_exists(course_code: str) -> bool:
    """
    Check if a syllabus already exists in the syllabuses table for this course_code.
    Used to prevent redundant reprocessing of already-completed courses.

    Args:
        course_code: Unique course identifier

    Returns:
        True if a syllabus record exists, False otherwise.

    Raises:
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError(
        "check_syllabus_exists: PostgreSQL not yet connected. "
        "Use MockDBWriter.check_syllabus_exists() in mock mode."
    )


# ---------------------------------------------------------------------------
# Phase 2 Operations
# ---------------------------------------------------------------------------

def read_syllabus(course_code: str) -> dict:
    """
    Read the Phase 1 syllabus from the syllabuses table.
    Called at Phase 2 entry by the parallel evaluator nodes.

    Args:
        course_code: Unique course identifier

    Returns:
        SyllabusDraft dict (same schema as what Phase 1 wrote)

    Raises:
        KeyError: if no syllabus found for course_code
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("read_syllabus: PostgreSQL not yet connected.")


def write_refined_syllabus(
    syllabus: dict,
    course_code: str,
    evaluation_results: dict
) -> str:
    """
    Write the Phase 2 refined/approved syllabus to the refined_syllabuses table.

    Args:
        syllabus: Refined SyllabusDraft as dict
        course_code: Unique course identifier
        evaluation_results: Dict of {evaluator_name: {pass: bool, feedback: str}}
                            for all four Phase 2 evaluator nodes

    Returns:
        record_id: Confirming successful write.

    Raises:
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("write_refined_syllabus: PostgreSQL not yet connected.")


# ---------------------------------------------------------------------------
# Phase 3 Operations
# ---------------------------------------------------------------------------

def read_refined_syllabus(course_code: str) -> dict:
    """
    Read the Phase 2 refined syllabus from the refined_syllabuses table.
    Called at Phase 3 entry by the CO generation agent.

    Args:
        course_code: Unique course identifier

    Returns:
        Refined SyllabusDraft dict

    Raises:
        KeyError: if no refined syllabus found for course_code
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("read_refined_syllabus: PostgreSQL not yet connected.")


def write_course_outcomes(cos: dict, course_code: str) -> str:
    """
    Write the Phase 3 Course Outcomes and Sub-COs to the course_outcomes table.

    Args:
        cos: CourseOutcomes dict — list of COs with Bloom's level, verbs, sub-COs
        course_code: Unique course identifier

    Returns:
        record_id: Confirming successful write.

    Raises:
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("write_course_outcomes: PostgreSQL not yet connected.")


# ---------------------------------------------------------------------------
# Phase 4 Operations
# ---------------------------------------------------------------------------

def read_course_outcomes(course_code: str) -> dict:
    """
    Read the Phase 3 course outcomes from the course_outcomes table.
    Called by Phase 4 alongside read_refined_syllabus.

    Args:
        course_code: Unique course identifier

    Returns:
        CourseOutcomes dict

    Raises:
        KeyError: if no outcomes found for course_code
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("read_course_outcomes: PostgreSQL not yet connected.")


def write_lecture_plan(lecture_plan: list[dict], course_code: str) -> str:
    """
    Write the Phase 4 lecture plan array to the lecture_plans table.

    Args:
        lecture_plan: List of lecture dicts, each with lecture_number, title,
                      subtopics, duration_minutes, cos_addressed, bloom_levels_targeted
        course_code: Unique course identifier

    Returns:
        record_id: Confirming successful write.

    Raises:
        ConnectionError: if DB connection fails
        ValueError: if lecture_plan is empty
    """
    raise NotImplementedError("write_lecture_plan: PostgreSQL not yet connected.")


# ---------------------------------------------------------------------------
# Phase 5a Operations
# ---------------------------------------------------------------------------

def read_lecture_plan(course_code: str) -> list[dict]:
    """
    Read the full lecture plan array for a course.
    Called by Phase 5a (one lecture at a time) and Phase 5b.

    Args:
        course_code: Unique course identifier

    Returns:
        List of lecture plan dicts (all lectures for the course)

    Raises:
        KeyError: if no lecture plan found for course_code
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("read_lecture_plan: PostgreSQL not yet connected.")


def write_ppt_content(
    ppt_content: dict,
    course_code: str,
    lecture_number: int
) -> str:
    """
    Write the structured PPT content for one lecture to the ppt_content table.
    This is the intermediate structured data (slide JSON) before PPTX rendering.

    Args:
        ppt_content: Structured slide data dict produced by Phase 5a assembly node
        course_code: Unique course identifier
        lecture_number: Which lecture this content belongs to (1-indexed)

    Returns:
        record_id: Confirming successful write.

    Raises:
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("write_ppt_content: PostgreSQL not yet connected.")


# ---------------------------------------------------------------------------
# Phase 5b Operations
# ---------------------------------------------------------------------------

def read_ppt_content(course_code: str, lecture_number: int) -> dict:
    """
    Read the structured PPT content for a specific lecture.
    Called by Phase 5b's Notes Orchestrator to package subtopic bundles.

    Args:
        course_code: Unique course identifier
        lecture_number: Which lecture to read (1-indexed)

    Returns:
        Structured PPT content dict for the specified lecture

    Raises:
        KeyError: if no PPT content found for this course/lecture combination
        ConnectionError: if DB connection fails
    """
    raise NotImplementedError("read_ppt_content: PostgreSQL not yet connected.")


# ---------------------------------------------------------------------------
# Pipeline Run Tracking (used by all phases for observability)
# ---------------------------------------------------------------------------

def log_phase_start(course_code: str, phase: str, run_id: str) -> None:
    """
    Log the start of a pipeline phase to the pipeline_runs table.

    Args:
        course_code: Unique course identifier
        phase: Phase name, e.g. "phase1", "phase2", "phase5a"
        run_id: Unique identifier for this pipeline run (UUID)
    """
    raise NotImplementedError("log_phase_start: PostgreSQL not yet connected.")


def log_phase_complete(run_id: str, status: str, metadata: Optional[dict] = None) -> None:
    """
    Log the completion of a pipeline phase and record status + metadata.

    Args:
        run_id: Run identifier from log_phase_start
        status: "completed" | "failed" | "force_passed"
        metadata: Optional dict of observability data (iteration_count, gap_count, etc.)
    """
    raise NotImplementedError("log_phase_complete: PostgreSQL not yet connected.")


# ---------------------------------------------------------------------------
# TODO: Real implementation notes
# ---------------------------------------------------------------------------
# When PostgreSQL is provisioned:
#
# 1. pip install psycopg2-binary (or asyncpg for async)
# 2. Connection pool: use psycopg2.pool.ThreadedConnectionPool or SQLAlchemy engine
# 3. All JSONB writes: json.dumps(data) → store as string in JSONB column
# 4. All reads: cursor.fetchone() → json.loads() → return dict
# 5. Schema DDL: CREATE TABLE IF NOT EXISTS syllabuses (
#       course_code TEXT PRIMARY KEY,
#       syllabus JSONB NOT NULL,
#       phase_status TEXT NOT NULL,
#       iteration_count INTEGER NOT NULL,
#       created_at TIMESTAMPTZ DEFAULT NOW()
#    );
#    (Similar for all other tables — DDL to be placed in db/schema.sql)
# 6. No node or graph code changes when switching from mock to real —
#    only dependencies.py factory functions need to return MCPPostgresWriter.
