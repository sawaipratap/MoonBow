"""
filesystem_mcp — File System MCP Server Package

Exposes read/write operations for MinIO (S3-compatible) object storage.
Used by all phases for skill loading, and by Phase 1 for curriculum reading,
Phase 5a/5b for generated file storage.

Import the server functions directly:
    from mcp.filesystem_mcp.server import read_curriculum, read_skill, write_file, list_skills
"""

from mcp.filesystem_mcp.server import (
    read_curriculum,
    read_skill,
    write_file,
    list_skills,
)

__all__ = [
    "read_curriculum",
    "read_skill",
    "write_file",
    "list_skills",
]
