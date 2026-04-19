"""
Reference Database MCP Server
==============================
Provides lookup operations against a curated internal database of academic
reference materials — accreditation standards, benchmark curricula, and
domain-specific learning outcome frameworks.

Connects to: Internal Reference DB (PostgreSQL or document store TBD)

Operations exposed to agents:
  - lookup_accreditation_standards(domain, level)     → dict   [Phase 2, Phase 3]
  - lookup_benchmark_curriculum(domain, level)        → dict   [Phase 2 — Relevance Evaluator]
  - lookup_co_frameworks(domain, accreditation_body)  → dict   [Phase 3 — CO agent, optional]

Why this is an MCP tool and NOT a skill:
  - The reference DB is live and grows as more standards are added — not static text
  - It is too large to inject fully into context; agents query only the slice they need
  - Agents actively decide whether to call it based on the domain and level they are evaluating
  - Results change as accreditation bodies update their frameworks

Phases that use this server:
  - Phase 2: Relevance Evaluator node — checks syllabus against benchmark curricula
             and accreditation standards for the domain
  - Phase 3: CO generation agent — optionally verifies COs against accreditation CO frameworks
             (agent decides at runtime whether this lookup is needed)
"""

import os
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REFDB_HOST: str = os.getenv("REFDB_HOST", "localhost")
REFDB_PORT: int = int(os.getenv("REFDB_PORT", "5432"))
REFDB_NAME: str = os.getenv("REFDB_NAME", "moonbow_refdb")
REFDB_USER: str = os.getenv("REFDB_USER", "refdb_user")
REFDB_PASSWORD: str = os.getenv("REFDB_PASSWORD", "")

# Supported accreditation bodies
SUPPORTED_ACCREDITATION_BODIES = ["NBA", "NAAC", "ABET", "AACSB", "UGC"]

# Supported academic domains (expand as more curricula are ingested)
SUPPORTED_DOMAINS = [
    "Computer Science",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Mathematics",
    "Physics",
    "Biotechnology",
    "Civil Engineering",
    "Data Science",
    "Electronics and Communication",
    "Chemical Engineering",
]


# ---------------------------------------------------------------------------
# Operation 1 — Accreditation Standards Lookup
# Used by: Phase 2 Relevance Evaluator, Phase 3 CO agent (optional)
# ---------------------------------------------------------------------------

def lookup_accreditation_standards(
    domain: str,
    level: str,
    accreditation_body: str = "NBA"
) -> dict:
    """
    Retrieve accreditation standards for a specific domain and academic level.

    Phase 2's Relevance Evaluator calls this to check whether the expanded
    syllabus aligns with what accreditation bodies expect for this domain/level
    combination. Phase 3's CO agent may call this to verify CO structure
    against accreditation-mandated PO (Program Outcome) mappings.

    Args:
        domain: Academic domain of the course, e.g. "Computer Science",
                "Electrical Engineering". Use values from SUPPORTED_DOMAINS.
        level: Academic level — "UG", "PG", or "PhD"
        accreditation_body: Which body's standards to retrieve.
                            Default "NBA" (National Board of Accreditation, India).
                            Options: "NBA", "NAAC", "ABET", "AACSB", "UGC"

    Returns:
        dict with structure:
        {
            "domain": str,
            "level": str,
            "accreditation_body": str,
            "program_outcomes": [
                {
                    "po_number": int,
                    "description": str,
                    "bloom_levels_expected": ["Apply", "Analyze"]
                }
            ],
            "mandatory_topics": [str],          # topics that MUST appear in any course of this type
            "recommended_topics": [str],         # topics that should appear for full alignment
            "credit_hour_norms": {
                "min": int,
                "max": int,
                "typical": int
            },
            "retrieved_at": str                  # ISO timestamp of the lookup
        }

    Raises:
        ValueError: if domain or level is not in supported lists
        LookupError: if no standards found for this domain/level/body combination
        ConnectionError: if Reference DB is unreachable
    """
    raise NotImplementedError(
        "lookup_accreditation_standards: Reference DB not yet connected. "
        "Implement using DB client when reference data is loaded."
    )


# ---------------------------------------------------------------------------
# Operation 2 — Benchmark Curriculum Lookup
# Used by: Phase 2 Relevance Evaluator node
# ---------------------------------------------------------------------------

def lookup_benchmark_curriculum(
    domain: str,
    level: str,
    top_k: int = 3
) -> dict:
    """
    Retrieve benchmark curricula from reputable institutions for a given
    domain and academic level. Used by Phase 2's Relevance Evaluator to
    compare the expanded syllabus against what leading institutions teach.

    The Relevance Evaluator uses this to identify:
    - Topics prominent in benchmark curricula that are conspicuously absent
    - Topics in the expanded syllabus that are outdated or non-standard
    - Whether the course's scope is too broad or too narrow relative to benchmarks

    Args:
        domain: Academic domain of the course, e.g. "Computer Science"
        level: "UG", "PG", or "PhD"
        top_k: Number of benchmark curricula to return (1–5). Default 3.
               More benchmarks give richer comparison but increase context size.

    Returns:
        dict with structure:
        {
            "domain": str,
            "level": str,
            "benchmarks": [
                {
                    "institution": str,           # e.g. "MIT", "IIT Bombay", "Stanford"
                    "course_name": str,
                    "credit_hours": int,
                    "core_topics": [str],          # main topic areas in this benchmark
                    "notable_inclusions": [str],   # topics this benchmark includes that are often missed
                    "source_url": str              # reference URL if publicly available
                }
            ],
            "consensus_topics": [str],             # topics appearing in ≥2 of the benchmarks
            "rarely_included": [str],              # topics in the input syllabus not common in benchmarks
            "retrieved_at": str
        }

    Raises:
        ValueError: if domain or level not supported, or top_k out of range
        LookupError: if no benchmark curricula exist for this domain/level
        ConnectionError: if Reference DB is unreachable
    """
    raise NotImplementedError(
        "lookup_benchmark_curriculum: Reference DB not yet connected. "
        "Implement using DB client when benchmark data is loaded."
    )


# ---------------------------------------------------------------------------
# Operation 3 — CO Framework Lookup
# Used by: Phase 3 CO agent (agent decides at runtime whether to call)
# ---------------------------------------------------------------------------

def lookup_co_frameworks(
    domain: str,
    accreditation_body: str = "NBA"
) -> dict:
    """
    Retrieve CO (Course Outcome) writing frameworks and PO (Program Outcome)
    mapping guidelines for a domain from a specific accreditation body.

    Phase 3's CO generation agent calls this when it needs to verify that
    the COs it is drafting are correctly structured for accreditation compliance.
    This is a tool — the agent decides whether to invoke it based on the course
    domain and whether accreditation alignment is critical.

    Args:
        domain: Academic domain of the course
        accreditation_body: "NBA", "NAAC", "ABET", "AACSB", or "UGC"

    Returns:
        dict with structure:
        {
            "domain": str,
            "accreditation_body": str,
            "co_writing_guidelines": str,          # institution-specific CO writing rules
            "po_list": [
                {
                    "po_number": int,
                    "po_statement": str,
                    "typical_bloom_range": [str]   # e.g. ["Apply", "Analyze", "Evaluate"]
                }
            ],
            "co_po_mapping_examples": [
                {
                    "example_co": str,
                    "maps_to_po": [int],
                    "bloom_level": str
                }
            ],
            "min_cos_required": int,               # minimum number of COs required by body
            "max_cos_allowed": int,
            "retrieved_at": str
        }

    Raises:
        ValueError: if domain or accreditation_body not supported
        LookupError: if no framework found for this combination
        ConnectionError: if Reference DB is unreachable
    """
    raise NotImplementedError(
        "lookup_co_frameworks: Reference DB not yet connected. "
        "Implement using DB client when CO framework data is loaded."
    )


# ---------------------------------------------------------------------------
# TODO: Real implementation notes
# ---------------------------------------------------------------------------
# Reference DB data loading plan:
#
# 1. NBA/NAAC standards: manually curated from official documents →
#    stored in refdb.accreditation_standards table as JSONB
#    Schema: (id, domain, level, body, standards_json, updated_at)
#
# 2. Benchmark curricula: scraped/curated from MIT OpenCourseWare, IIT NPTEL,
#    Stanford Online, etc. → stored in refdb.benchmark_curricula table
#    Schema: (id, institution, domain, level, course_name, topics_json, source_url, updated_at)
#
# 3. CO frameworks: curated NBA graduate attribute mappings →
#    stored in refdb.co_frameworks table
#    Schema: (id, domain, body, framework_json, updated_at)
#
# Implementation:
# - Use psycopg2 or asyncpg to connect to REFDB
# - All lookups return Python dicts (JSON-deserialized from JSONB columns)
# - Add an in-memory TTL cache (functools.lru_cache or cachetools.TTLCache)
#   because these lookups are read-heavy and the data changes infrequently
#
# Agents access this via the tool_runner interface (NOT the skill_loader interface)
# — because this is a tool the agent decides to call, not a skill injected before reasoning.
#
# In Phase 2:
#   The Relevance Evaluator node calls lookup_benchmark_curriculum() and
#   lookup_accreditation_standards() as part of its fixed evaluation logic.
#   It is NOT optional in Phase 2 — the node always calls these.
#
# In Phase 3:
#   The CO agent calls lookup_co_frameworks() only if it judges the domain
#   requires strict accreditation alignment. The agent decides at runtime.
