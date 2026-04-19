"""
qdrant_mcp — Qdrant Vector Search MCP Server Package

Provides cross-curriculum similarity search for Phase 1's Expander node.
Used as a TOOL (not a skill) — the Expander decides at runtime whether
to call it when the course has listed prerequisites.

This allows the Expander to check whether a topic it is about to expand
is already deeply covered in a prerequisite course, preventing duplication.

Import:
    from mcp.qdrant_mcp.server import run_similarity_search
"""

from mcp.qdrant_mcp.server import run_similarity_search

__all__ = ["run_similarity_search"]
