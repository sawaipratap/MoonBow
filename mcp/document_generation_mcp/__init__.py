"""
document_generation_mcp — Document Generation MCP Server Package

Renders structured agent output into actual files:
  - render_pptx() → raw PPTX bytes  (Phase 5a)
  - render_notes() → MD + PDF bytes  (Phase 5b)

Agents pass structured JSON content here. This server handles formatting.
The returned bytes are then stored by filesystem_mcp.write_file() in MinIO.

Import:
    from mcp.document_generation_mcp.server import render_pptx, render_notes
"""

from mcp.document_generation_mcp.server import render_pptx, render_notes

__all__ = ["render_pptx", "render_notes"]
