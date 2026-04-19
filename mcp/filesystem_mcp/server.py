"""
File System MCP Server
======================
Provides a standardised interface for all file I/O in the pipeline.

Connects to: MinIO (S3-compatible object storage)

Operations exposed to agents:
  - read_curriculum(file_path)       → str   [Phase 1]
  - read_skill(skill_name)           → str   [All phases — skill injection]
  - write_file(dest_path, content)   → str   [Phase 5a PPTX, Phase 5b Notes]
  - list_skills()                    → list  [Debugging / validation]

Why MCP and not direct file access:
  - Decouples agent code from storage backend (MinIO → S3 swap = only this file changes)
  - Skills are read at runtime from MinIO → updates take effect without redeployment
  - Single canonical place for all file-related auth, retry, and error handling

Phases that use this server:
  - Phase 1: read_curriculum, read_skill
  - Phase 2: read_skill
  - Phase 3: read_skill
  - Phase 4: read_skill (none needed currently)
  - Phase 5a: read_skill, write_file (PPTX)
  - Phase 5b: read_skill, write_file (Notes MD/PDF)
"""

import os
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration — populated from environment or MCP server config at runtime
# ---------------------------------------------------------------------------

MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")

CURRICULUM_BUCKET: str = os.getenv("CURRICULUM_BUCKET", "curricula")
SKILLS_BUCKET: str = os.getenv("SKILLS_BUCKET", "skills")
OUTPUT_BUCKET: str = os.getenv("OUTPUT_BUCKET", "generated-content")

# Local fallback paths used when DEPENDENCY_MODE=mock
LOCAL_SKILLS_DIR: str = os.getenv(
    "LOCAL_SKILLS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "skills", "knowledge")
)
LOCAL_CURRICULUM_DIR: str = os.getenv("LOCAL_CURRICULUM_DIR", "")


# ---------------------------------------------------------------------------
# Interface contract (mirrors interfaces/file_reader.py in phase1)
# ---------------------------------------------------------------------------

def read_curriculum(file_path: str) -> str:
    """
    Read a curriculum MD or PDF file from MinIO and return its full text.

    Args:
        file_path: Object path within CURRICULUM_BUCKET, e.g. "cs/CSE2001_curriculum.md"
                   PDF files are extracted to plain text before returning.

    Returns:
        Full text content of the curriculum as a string.

    Raises:
        FileNotFoundError: if the object does not exist in the bucket
        ValueError: if the file format is not supported (only .md and .pdf)
        ConnectionError: if MinIO is unreachable
    """
    raise NotImplementedError(
        "read_curriculum: MinIO client not yet connected. "
        "Use MockFileReader via dependencies.py in mock mode."
    )


def read_skill(skill_name: str) -> str:
    """
    Read a skill MD file by name from the skills bucket in MinIO.

    Skills are always read fresh on each agent invocation — no caching.
    This ensures that skill updates take effect immediately without redeployment.

    Args:
        skill_name: Filename of the skill, e.g. "academic_level_calibrator.md"
                    Do NOT include bucket prefix or path — name only.

    Returns:
        Full markdown content of the skill file as a string.

    Raises:
        FileNotFoundError: if the skill does not exist in the skills bucket
        ConnectionError: if MinIO is unreachable
    """
    raise NotImplementedError(
        "read_skill: MinIO client not yet connected. "
        "Use MockSkillLoader via dependencies.py in mock mode."
    )


def write_file(dest_path: str, content: bytes, content_type: str = "application/octet-stream") -> str:
    """
    Write a generated file (PPTX, PDF, MD) to the OUTPUT_BUCKET in MinIO.

    Used by Phase 5a to store PPTX files and Phase 5b to store notes files.

    Args:
        dest_path: Target object path within OUTPUT_BUCKET.
                   Convention: "{course_code}/lecture_{N}/{filename}"
                   e.g. "CSE2001/lecture_3/lecture_3_slides.pptx"
        content: Raw bytes of the file to write.
        content_type: MIME type of the content.
                      - PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                      - PDF:  "application/pdf"
                      - MD:   "text/markdown"

    Returns:
        Full MinIO URL to the stored object, e.g.
        "http://minio:9000/generated-content/CSE2001/lecture_3/lecture_3_slides.pptx"

    Raises:
        ConnectionError: if MinIO is unreachable
        ValueError: if content is empty
    """
    raise NotImplementedError(
        "write_file: MinIO client not yet connected. "
        "Implement using minio-py client once MinIO is provisioned."
    )


def list_skills() -> list[str]:
    """
    Return a list of all skill filenames available in the skills bucket.

    Returns:
        List of skill filenames, e.g. ["academic_level_calibrator.md", "blooms_taxonomy.md"]
        Empty list if no skills are found.

    Raises:
        ConnectionError: if MinIO is unreachable
    """
    raise NotImplementedError(
        "list_skills: MinIO client not yet connected. "
        "In mock mode, MockSkillLoader reads from LOCAL_SKILLS_DIR directly."
    )


# ---------------------------------------------------------------------------
# TODO: Real implementation notes
# ---------------------------------------------------------------------------
# When MinIO is provisioned:
#
# 1. pip install minio
# 2. Initialize client:
#    from minio import Minio
#    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
#
# 3. read_curriculum: client.get_object(CURRICULUM_BUCKET, file_path) → read bytes → decode
#    For PDF: use pdfminer.six or pypdf to extract text
#
# 4. read_skill: client.get_object(SKILLS_BUCKET, skill_name) → read bytes → decode utf-8
#
# 5. write_file: client.put_object(OUTPUT_BUCKET, dest_path, io.BytesIO(content), len(content), content_type)
#    Return f"{MINIO_ENDPOINT}/{OUTPUT_BUCKET}/{dest_path}"
#
# 6. list_skills: client.list_objects(SKILLS_BUCKET) → [obj.object_name for obj in objects]
#
# No node or graph code changes when switching from mock to real —
# only dependencies.py factory functions need to return MCPFileReader / MCPSkillLoader.
