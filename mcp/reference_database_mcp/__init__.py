"""
reference_database_mcp — Reference Database MCP Server Package

Exposes lookup operations against the curated internal database of
accreditation standards and benchmark curricula.

This server is accessed as a TOOL (not a skill):
  - Phase 2 Relevance Evaluator: always calls lookup_benchmark_curriculum
    and lookup_accreditation_standards as part of its evaluation logic
  - Phase 3 CO agent: optionally calls lookup_co_frameworks at runtime

Import the server functions directly:
    from mcp.reference_database_mcp.server import (
        lookup_accreditation_standards,
        lookup_benchmark_curriculum,
        lookup_co_frameworks,
    )
"""

from mcp.reference_database_mcp.server import (
    lookup_accreditation_standards,
    lookup_benchmark_curriculum,
    lookup_co_frameworks,
)

__all__ = [
    "lookup_accreditation_standards",
    "lookup_benchmark_curriculum",
    "lookup_co_frameworks",
]
