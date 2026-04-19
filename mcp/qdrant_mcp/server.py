"""
Qdrant MCP Server
=================
Provides cross-curriculum similarity search over a Qdrant vector database
that stores topic embeddings from all 200+ processed course curricula.

Connects to: Qdrant vector database (self-hosted on DGX cluster)

Operation exposed to agents:
  - run_similarity_search(topics, top_k)  → list[dict]   [Phase 1 — Expander node]

Why this is a TOOL and NOT a skill:
  - The Qdrant index is a live, growing database. Results change as more courses
    are processed. It cannot be a static skill file.
  - The Expander decides at runtime whether to call it — only invoked when
    the course has listed prerequisites and there's a risk of topic duplication.
  - Empty results (no similar topics found) are a valid and common outcome.

When the Expander uses it:
  - The Expander sees that the course has prerequisite courses listed in metadata.
  - It queries Qdrant with the topic names it is about to expand.
  - If Qdrant returns that "Linear Algebra" is covered at intermediate level in
    "MAT1001 — Engineering Mathematics I" (a prerequisite), the Expander knows
    NOT to re-expand it as a primary subtopic.
  - Results are injected into the expander prompt context under:
    "## Topics Already Covered in Prerequisite Courses (Avoid Duplication)"

Phases that use this server:
  - Phase 1: Expander node (tool call, agent-decided, non-fatal if unavailable)

How topics get INTO Qdrant:
  - After Phase 1 completes for a course, a post-processing step (not part of the
    Phase 1 graph) embeds all subtopic names and descriptions from the validated
    SyllabusDraft and upserts them into the Qdrant collection.
  - Each vector point carries a payload: course_code, course_name, topic_name,
    subtopic_name, coverage_level, bloom_level (once Phase 3 is complete).
  - This means early runs have sparse data; the index improves as more courses
    are processed. The Expander handles empty results gracefully.
"""

import os
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", None)  # None for local, set for cloud
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "course_topics")

# Embedding model used to generate vectors for search
# Must match the model used when topics were upserted into Qdrant
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Similarity score threshold — results below this are discarded as noise
SIMILARITY_THRESHOLD: float = float(os.getenv("QDRANT_SIMILARITY_THRESHOLD", "0.75"))


# ---------------------------------------------------------------------------
# Core Operation: Similarity Search
# Used by: Phase 1 Expander node via ToolRunner.run_similarity_search()
# ---------------------------------------------------------------------------

def run_similarity_search(
    topics: list[str],
    top_k: int = 5,
    exclude_course_code: Optional[str] = None
) -> list[dict]:
    """
    Search the Qdrant cross-curriculum index for topics similar to the
    given topic names, returning matches from OTHER courses.

    Called by the Phase 1 Expander when the course being processed has
    prerequisite courses listed in metadata. Used to avoid duplicating
    content already covered in prerequisite courses.

    Args:
        topics: List of topic or subtopic names to search for.
                E.g. ["Linear Algebra", "Matrix Operations", "Eigenvalues"]
                Each topic is embedded separately; results are merged.
        top_k: Maximum number of similar results to return PER topic.
               Total results may be up to len(topics) * top_k before dedup.
               Default 5. Range 1–20.
        exclude_course_code: Course code to exclude from results.
                             Pass the current course's code to avoid
                             matching against itself (if it was previously processed).
                             E.g. "CSE2001"

    Returns:
        List of dicts, deduplicated and sorted by similarity_score descending:
        [
            {
                "topic": str,           # the query topic that matched
                "matched_subtopic": str, # exact subtopic name in the other course
                "course_code": str,      # e.g. "MAT1001"
                "course_name": str,      # e.g. "Engineering Mathematics I"
                "similarity_score": float, # 0.0–1.0, higher = more similar
                "coverage_level": str,   # "introductory" | "intermediate" | "advanced"
                "unit_name": str        # which unit the matched subtopic belongs to
            },
            ...
        ]
        Returns empty list [] if:
        - No matches above SIMILARITY_THRESHOLD are found
        - Qdrant collection is empty (early pipeline state)
        - topics list is empty

    Raises:
        ConnectionError: if Qdrant is unreachable.
                         NOTE: The Expander catches this and continues
                         with empty results — this error is NON-FATAL.

    Example result interpretation:
        Query topic: "Linear Algebra"
        Result: {
            "topic": "Linear Algebra",
            "matched_subtopic": "Matrix Operations and Linear Systems",
            "course_code": "MAT1001",
            "course_name": "Engineering Mathematics I",
            "similarity_score": 0.91,
            "coverage_level": "intermediate",
            "unit_name": "Unit 3: Linear Systems"
        }
        → Expander should NOT re-expand "Linear Algebra" as a primary subtopic
          since it's covered at intermediate level in a listed prerequisite.
    """
    raise NotImplementedError(
        "run_similarity_search: Qdrant client not yet connected.\n"
        "Use MockToolRunner (returns []) via dependencies.py in mock mode.\n"
        "The Expander node handles empty results gracefully — Phase 1 will\n"
        "still work correctly; the expander just won't have cross-curriculum context."
    )


# ---------------------------------------------------------------------------
# Upsert Operation: Index a processed course's topics into Qdrant
# Called by the post-Phase-1 indexer (NOT by Phase 1 graph itself)
# ---------------------------------------------------------------------------

def upsert_course_topics(
    course_code: str,
    course_name: str,
    syllabus_topics: list[dict]
) -> int:
    """
    Embed and upsert all subtopics from a validated SyllabusDraft into Qdrant.

    This is called AFTER Phase 1 completes successfully for a course, NOT
    during the Phase 1 graph execution. It is part of the post-processing
    pipeline that keeps the cross-curriculum index up to date.

    Args:
        course_code: E.g. "MATH2059"
        course_name: E.g. "Linear Algebra"
        syllabus_topics: The `topics` list from SyllabusDraft.model_dump()
                         Each topic has: topic_name, unit_number, subtopics list

    Returns:
        Number of vectors upserted into Qdrant.

    Raises:
        ConnectionError: if Qdrant is unreachable
        ValueError: if syllabus_topics is empty

    Each vector point payload stored in Qdrant:
        {
            "course_code": str,
            "course_name": str,
            "unit_name": str,
            "subtopic_name": str,
            "coverage_level": str,    # from subtopic.depth_level
            "indexed_at": str         # ISO timestamp
        }
    The vector itself: embedding of f"{subtopic_name}: {subtopic_description}"
    using EMBEDDING_MODEL.
    """
    raise NotImplementedError(
        "upsert_course_topics: Qdrant client not yet connected.\n"
        "Implement using qdrant-client Python SDK when Qdrant is provisioned."
    )


# ---------------------------------------------------------------------------
# TODO: Real implementation notes
# ---------------------------------------------------------------------------
# 1. pip install qdrant-client sentence-transformers
#
# 2. Initialize Qdrant client:
#    from qdrant_client import QdrantClient
#    from qdrant_client.models import Distance, VectorParams, PointStruct
#    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY)
#
# 3. Create collection (one-time setup):
#    client.recreate_collection(
#        collection_name=QDRANT_COLLECTION,
#        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
#        # 384 = all-MiniLM-L6-v2 embedding dimension
#    )
#
# 4. run_similarity_search implementation:
#    from sentence_transformers import SentenceTransformer
#    model = SentenceTransformer(EMBEDDING_MODEL)
#    results = []
#    for topic in topics:
#        vector = model.encode(topic).tolist()
#        hits = client.search(
#            collection_name=QDRANT_COLLECTION,
#            query_vector=vector,
#            limit=top_k,
#            score_threshold=SIMILARITY_THRESHOLD,
#            query_filter=Filter(must_not=[FieldCondition(key="course_code",
#                                match=MatchValue(value=exclude_course_code))])
#                                if exclude_course_code else None
#        )
#        for hit in hits:
#            results.append({
#                "topic": topic,
#                "matched_subtopic": hit.payload["subtopic_name"],
#                "course_code": hit.payload["course_code"],
#                "course_name": hit.payload["course_name"],
#                "similarity_score": hit.score,
#                "coverage_level": hit.payload["coverage_level"],
#                "unit_name": hit.payload["unit_name"]
#            })
#    # Deduplicate by (course_code, matched_subtopic), keep highest score
#    return sorted(results, key=lambda x: x["similarity_score"], reverse=True)
#
# 5. upsert_course_topics implementation:
#    vectors = []
#    for topic in syllabus_topics:
#        for subtopic in topic["subtopics"]:
#            text = f"{subtopic['subtopic_name']}: {subtopic['description']}"
#            vector = model.encode(text).tolist()
#            vectors.append(PointStruct(
#                id=hash(f"{course_code}:{subtopic['subtopic_name']}") % (2**63),
#                vector=vector,
#                payload={
#                    "course_code": course_code,
#                    "course_name": course_name,
#                    "unit_name": topic["topic_name"],
#                    "subtopic_name": subtopic["subtopic_name"],
#                    "coverage_level": subtopic["depth_level"],
#                    "indexed_at": datetime.now().isoformat()
#                }
#            ))
#    client.upsert(collection_name=QDRANT_COLLECTION, points=vectors)
#    return len(vectors)
#
# 6. In dependencies.py for Phase 1 (when DEPENDENCY_MODE="real"):
#    def get_tool_runner() -> ToolRunner:
#        from mcp.qdrant_mcp.server import run_similarity_search
#        class MCPToolRunnerAdapter(ToolRunner):
#            def run_similarity_search(self, topics, top_k=5):
#                return run_similarity_search(topics, top_k)
#        return MCPToolRunnerAdapter()
#
# IMPORTANT: The Expander catches ConnectionError from tool_runner non-fatally:
#   try:
#       similar_topics = tool_runner.run_similarity_search(...)
#   except Exception as e:
#       print(f"[expander] Similarity search failed (non-fatal): {e}")
#       similar_topics = []
# Never let Qdrant failures crash Phase 1.
