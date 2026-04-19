"""
quality_plagiarism_mcp — Quality / Plagiarism MCP Server Package

Provides content quality and originality checks for Phase 5b's QA gate:
  - check_quality()     → coverage verification against lecture plan
  - check_originality() → plagiarism/originality score

Both are always called by the QA gate (not optional).
Quality failures trigger targeted subtopic regeneration.
Originality failures flag sections for human review.

Import:
    from mcp.quality_plagiarism_mcp.server import check_quality, check_originality
"""

from mcp.quality_plagiarism_mcp.server import check_quality, check_originality

__all__ = ["check_quality", "check_originality"]
