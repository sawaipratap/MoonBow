# MoonBow — Complete Skills and MCP Usage Reference

## What This Document Is

This is the single source of truth for how every **skill file** and every **MCP server** in this project is used, by whom, and when. Every developer working on any phase should read this before writing a single node.

It covers everything built so far:
- `skills/knowledge/` — 2 knowledge skills (fully populated)
- `mcp/filesystem_mcp/` — file I/O for MinIO
- `mcp/postgresql_mcp/` — inter-phase structured state store
- `mcp/qdrant_mcp/` — cross-curriculum similarity search (Phase 1 tool)
- `mcp/reference_database_mcp/` — accreditation standards + benchmarks (Phase 2/3 tool)
- `mcp/document_generation_mcp/` — PPTX and notes file rendering (Phase 5a/5b)
- `mcp/quality_plagiarism_mcp/` — coverage + originality QA (Phase 5b)

---

## The Three-Layer Mental Model

Before anything else, understand these three things are NOT the same:

| Layer | What it is | How agent uses it | Decision required? |
|---|---|---|---|
| **Skill** | MD file with domain knowledge | Loaded once into prompt context before reasoning | No — always loaded if assigned to phase |
| **MCP (read/write)** | External system connector | Called at specific points in specific nodes | No — node always calls it at its defined point |
| **MCP (tool)** | External system connector | Agent decides at runtime whether to call | Yes — agent invokes based on what it encounters |

---

## Master Phase-to-Resource Map

```
Phase 1 — Syllabus Expansion (LangGraph)
├── Skills:    academic_level_calibrator.md
│              curriculum_parser_instructions.md
├── MCP read:  filesystem_mcp.read_curriculum()
│              filesystem_mcp.read_skill()
├── MCP write: postgresql_mcp.write_syllabus()
│              postgresql_mcp.check_syllabus_exists()
└── MCP tool:  qdrant_mcp.run_similarity_search()   ← agent-decided, non-fatal

Phase 2 — Syllabus Refinement (LangGraph)
├── Skills:    academic_level_calibrator.md          ← same file, reused
├── MCP read:  postgresql_mcp.read_syllabus()
│              filesystem_mcp.read_skill()
│              reference_database_mcp.lookup_benchmark_curriculum()
│              reference_database_mcp.lookup_accreditation_standards()
├── MCP write: postgresql_mcp.write_refined_syllabus()
└── MCP tool:  custom_tools_mcp (credit hour calc)   ← not yet built

Phase 3 — Course Outcomes + Bloom's (PhiData)
├── Skills:    blooms_taxonomy.md                    ← not yet populated
│              co_writing_guidelines.md              ← not yet populated
│              academic_level_calibrator.md          ← reused
├── MCP read:  filesystem_mcp.read_skill()
│              postgresql_mcp.read_refined_syllabus()
└── MCP tool:  reference_database_mcp.lookup_co_frameworks()  ← agent-decided

Phase 4 — Lecture Planning (Direct LLM)
├── Skills:    none
├── MCP read:  postgresql_mcp.read_refined_syllabus()
│              postgresql_mcp.read_course_outcomes()
└── MCP write: postgresql_mcp.write_lecture_plan()

Phase 5a — PPT Generation (LangGraph)
├── Skills:    slide_structure.md                   ← not yet populated
│              blooms_taxonomy.md                   ← not yet populated
│              continuity_guidelines.md             ← not yet populated
├── MCP read:  filesystem_mcp.read_skill()
│              postgresql_mcp.read_lecture_plan()
├── MCP write: postgresql_mcp.write_ppt_content()
│              filesystem_mcp.write_file()          (stores PPTX to MinIO)
├── MCP tool:  custom_tools_mcp (image/diagram search) ← not yet built
└── MCP call:  document_generation_mcp.render_pptx()

Phase 5b — Notes Generation (LangGraph)
├── Skills:    blooms_taxonomy.md                   ← not yet populated
│              academic_level_calibrator.md         ← reused
│              continuity_guidelines.md             ← not yet populated
├── MCP read:  filesystem_mcp.read_skill()
│              postgresql_mcp.read_lecture_plan()
│              postgresql_mcp.read_ppt_content()
├── MCP write: filesystem_mcp.write_file()          (stores Notes MD/PDF to MinIO)
├── MCP call:  document_generation_mcp.render_notes()
└── MCP gate:  quality_plagiarism_mcp.check_quality()
               quality_plagiarism_mcp.check_originality()
```

---

## Skills — Complete Reference

### `skills/knowledge/academic_level_calibrator.md`
**Status: ✅ Fully populated**

| Field | Value |
|---|---|
| Type | Knowledge skill — MD file, injected into prompt context |
| Loaded by | `skill_injector` node in every phase that uses it |
| State field | `state.level_calibrator_skill` |
| Phases | 1, 2, 3, 5b |

**What it contains:**
- Full definitions of UG, PG, PhD levels: depth, vocabulary, prior knowledge assumptions, estimated hours per subtopic (UG: 1–3h, PG: 2–5h, PhD: 3–8h)
- Calibration checklist: 5 questions agents must mentally run before finalising any content
- Common calibration errors table

**How each phase uses it:**

| Phase | Node | What it drives |
|---|---|---|
| 1 | `expander` | Sets `depth_level` and `estimated_hours` on each `Subtopic`. Controls vocabulary and description depth. |
| 1 | `gap_critic` | Evaluates whether expander's depth choices match the level. Source of `depth_mismatch` gap type. |
| 2 | `level_evaluator` | Checks subtopic descriptions, depth labels, and per-subtopic hours against level guidelines. Returns `pass/fail` + score. |
| 3 | CO agent | Ensures Course Outcomes are written at the right cognitive challenge for the level. |
| 5b | subtopic notes agents | Controls how deep and how technical generated notes explanations are. |

**What breaks if wrong:**
- Wrong hour ranges → Hours Evaluator fails good syllabuses (Phase 2)
- Missing a level section → LLM falls back to general knowledge, inconsistent depth
- Vocabulary expectations miscalibrated → false-positive or false-negative depth flags

---

### `skills/knowledge/curriculum_parser_instructions.md`
**Status: ✅ Fully populated**

| Field | Value |
|---|---|
| Type | Knowledge skill — MD file, injected into prompt context |
| Loaded by | `skill_injector` node in Phase 1 |
| State field | `state.parser_instructions_skill` |
| Phases | 1 only |

**What it contains:**
- Rules for extracting 8 metadata fields (course name, code, level, credit hours, domain, institution, semester, prerequisites) with inference rules for each
- Handling rules for: Roman numerals, abbreviations, L-T-P credit notation, flat topic lists (no unit structure), duplicate topics, vague entries like "Advanced Topics"
- Output contract: always return structured data, never raw text

**How Phase 1 uses it:**

The `curriculum_loader` has its own hardcoded extraction prompt for `CourseMetadata`. The skill handles something deeper: it is available to the **Expander** when it interprets the raw topic list. The Expander uses it to correctly handle flat lists, abbreviations, and vague entries during expansion — edge cases the metadata extraction prompt doesn't cover.

```
curriculum_loader  →  extracts CourseMetadata  (uses hardcoded prompt)
     ↓
skill_injector     →  loads curriculum_parser_instructions.md into state
     ↓
expander           →  uses skill context to correctly interpret topic list
```

**What breaks if wrong:**
- Missing flat-list grouping rules → arbitrary unit groupings → sequencing gaps in Phase 2
- Wrong abbreviation rules → inconsistent subtopic names propagate to Phase 5a slide titles
- No vague-entry guidance → expander skips "Advanced Topics" (coverage gap) or invents content (hallucination)

---

### `skills/knowledge/blooms_taxonomy.md`
**Status: 🔲 File exists, not yet populated**
Used by: Phase 3 (CO agent, primary), Phase 5a (slide objectives), Phase 5b (notes depth)

### `skills/knowledge/co_writing_guidelines.md`
**Status: 🔲 File exists, not yet populated**
Used by: Phase 3 exclusively

### `skills/knowledge/slide_structure.md`
**Status: 🔲 File exists, not yet populated**
Used by: Phase 5a exclusively

### `skills/knowledge/continuity_guidelines.md`
**Status: 🔲 File exists, not yet populated**
Used by: Phase 5a assembly node, Phase 5b notes assembler

---

## MCP Servers — Complete Reference

---

### `mcp/filesystem_mcp/`
**Status: ✅ Fully stubbed (all functions raise `NotImplementedError` — real impl = MinIO client)**

**Connects to:** MinIO object storage (S3-compatible)

#### Operations

| Function | Phases | Called by node | What it does |
|---|---|---|---|
| `read_curriculum(file_path)` | 1 | `curriculum_loader` | Reads raw curriculum MD or PDF from MinIO, returns plain text string. PDF → text extraction is the MCP's responsibility, not the node's. |
| `read_skill(skill_name)` | All | `skill_injector` | Reads a skill MD file by name from the skills bucket. Skills are read fresh every run — no caching — so file updates take effect immediately. |
| `write_file(dest_path, content, content_type)` | 5a, 5b | `output_writer` | Stores generated PPTX / MD / PDF bytes to MinIO. Returns the MinIO URL of the stored object. |
| `list_skills()` | Debug | — | Returns all skill filenames in the skills bucket. Used for validation. |

#### Phase 1 call chain (mock mode)

```python
# curriculum_loader_node():
file_reader = get_file_reader()              # → MockFileReader (reads from test_data/)
curriculum_text = file_reader.read_curriculum(state.curriculum_file_path)

# skill_injector_node():
skill_loader = get_skill_loader()            # → MockSkillLoader (reads from skills/knowledge/)
level_cal   = skill_loader.load("academic_level_calibrator.md")
parser_inst = skill_loader.load("curriculum_parser_instructions.md")
```

#### Phase 1 call chain (real mode — when MinIO is ready)

```python
# dependencies.py — already wired:
from mcp.filesystem_mcp.server import read_curriculum, read_skill
class MCPFileReaderAdapter(FileReader):
    def read_curriculum(self, fp): return read_curriculum(fp)
class MCPSkillLoaderAdapter(SkillLoader):
    def load(self, s): return read_skill(s)
```

**What breaks if wrong:**
- `read_curriculum` returns empty → `curriculum_loader` falls back to minimal `CourseMetadata`. Expander has nothing to expand. Force-pass with skeleton syllabus.
- `read_curriculum` raises `FileNotFoundError` → Phase 1 crashes at node 1.
- `read_skill` returns empty → Skill field in state is empty string. LLM loses its domain knowledge. Output quality degrades silently — hardest failure mode to detect.
- `read_skill` raises `FileNotFoundError` → `skill_injector` crashes. Entire phase blocked.

---

### `mcp/postgresql_mcp/`
**Status: ✅ Fully stubbed — all functions defined with correct signatures and raise `NotImplementedError`**

**Connects to:** PostgreSQL — the inter-phase structured state store

This is the **data bus between all phases**. Every phase reads its input from here and writes its output here. Phases are independently restartable because their inputs are always in PostgreSQL — a phase re-run never needs to re-run its predecessors.

#### All operations by phase

**Phase 1 (writes)**

| Function | Signature | What it stores |
|---|---|---|
| `check_syllabus_exists(course_code)` | `str → bool` | Guards against reprocessing already-done courses |
| `write_syllabus(syllabus, course_code, phase_status, iteration_count)` | `→ str (record_id)` | Stores `SyllabusDraft` JSON + phase metadata to `syllabuses` table |

**Phase 2 (reads Phase 1, writes Phase 2)**

| Function | Signature | What it does |
|---|---|---|
| `read_syllabus(course_code)` | `str → dict` | Reads the `SyllabusDraft` stored by Phase 1. Returns full record including `phase_status`. |
| `write_refined_syllabus(syllabus, course_code, evaluation_results)` | `→ str` | Stores approved syllabus + all four evaluator outputs to `refined_syllabuses` table |

**Phase 3 (reads Phase 2, writes Phase 3)**

| Function | Signature | What it does |
|---|---|---|
| `read_refined_syllabus(course_code)` | `str → dict` | Reads Phase 2 output |
| `write_course_outcomes(cos, course_code)` | `→ str` | Stores CO + Sub-CO JSON to `course_outcomes` table |

**Phase 4 (reads Phases 2+3, writes Phase 4)**

| Function | Signature | What it does |
|---|---|---|
| `read_refined_syllabus(course_code)` | — | Reads Phase 2 output |
| `read_course_outcomes(course_code)` | `str → dict` | Reads Phase 3 output |
| `write_lecture_plan(lecture_plan, course_code)` | `list[dict] → str` | Stores full lecture plan array to `lecture_plans` table |

**Phase 5a (reads Phase 4, writes 5a)**

| Function | Signature | What it does |
|---|---|---|
| `read_lecture_plan(course_code)` | `str → list[dict]` | Reads full lecture plan array |
| `write_ppt_content(ppt_content, course_code, lecture_number)` | `→ str` | Stores structured slide JSON per lecture (intermediate, before PPTX render) |

**Phase 5b (reads Phases 4 and 5a)**

| Function | Signature | What it does |
|---|---|---|
| `read_lecture_plan(course_code)` | — | Reads lecture plan |
| `read_ppt_content(course_code, lecture_number)` | `str, int → dict` | Reads Phase 5a structured slide data for a specific lecture |

**All phases (observability)**

| Function | What it does |
|---|---|
| `log_phase_start(course_code, phase, run_id)` | Records phase start in `pipeline_runs` table |
| `log_phase_complete(run_id, status, metadata)` | Records phase completion + iteration counts, gap counts, etc. |

#### Database schema (at a glance)

```
syllabuses          (course_code PK, syllabus JSONB, phase_status, iteration_count, created_at)
refined_syllabuses  (course_code PK, syllabus JSONB, evaluation_results JSONB, created_at)
course_outcomes     (course_code PK, outcomes JSONB, created_at)
lecture_plans       (course_code PK, plan JSONB, created_at)
ppt_content         (course_code, lecture_number, content JSONB, created_at)
pipeline_runs       (run_id PK, course_code, phase, status, started_at, completed_at, metadata JSONB)
```

#### Phase 1 call chain (mock mode)

```python
# output_writer_node():
db_writer = get_db_writer()              # → MockDBWriter (writes to phase1/mock_outputs/)
record_id = db_writer.write_syllabus(
    syllabus=state.syllabus_draft,
    course_code="MATH2059",
    phase_status="passed",
    iteration_count=2
)
# writes: phase1/mock_outputs/syllabus_mock_MATH2059_20260419_123542.json
```

#### Phase 1 call chain (real mode — already wired in `dependencies.py`)

```python
from mcp.postgresql_mcp.server import write_syllabus, check_syllabus_exists
class MCPDBWriterAdapter(DBWriter):
    def write_syllabus(self, s, c, p, i): return write_syllabus(s.model_dump(), c, p, i)
    def check_syllabus_exists(self, c): return check_syllabus_exists(c)
```

**What breaks if wrong:**
- `write_syllabus` fails → Phase 2 has no input, entire course is blocked
- `write_syllabus` writes malformed JSONB → Phase 2 evaluators all fail on corrupt data
- `read_syllabus` returns a record with `phase_status: "failed"` → Phase 2 proceeds on broken syllabus (Phase 2 should check this)
- `check_syllabus_exists` always `True` → all courses skipped; always `False` → all courses reprocessed

---

### `mcp/qdrant_mcp/`
**Status: ✅ Fully stubbed — directory created, server defined, raises `NotImplementedError`**

**Was missing entirely before this session. This was the only Phase 1 dependency with zero implementation.**

**Connects to:** Qdrant vector database on DGX cluster

**Type:** TOOL (agent-decided, non-fatal on failure)

#### Operation

| Function | Signature | What it does |
|---|---|---|
| `run_similarity_search(topics, top_k, exclude_course_code)` | `list[str], int, str → list[dict]` | Searches cross-curriculum topic index for courses that already cover the given topics |
| `upsert_course_topics(course_code, course_name, syllabus_topics)` | `→ int` | Post-Phase-1 indexer — embeds subtopics and upserts into Qdrant. NOT called by Phase 1 graph itself. |

#### How Phase 1 uses it

```python
# In expander_node():
# Only triggered when course has prerequisite courses listed
if state.course_metadata and state.course_metadata.prerequisites:
    try:
        similar_topics = tool_runner.run_similarity_search(
            topics=[curriculum_words],
            top_k=5,
            exclude_course_code=state.course_metadata.course_code
        )
    except Exception as e:
        print(f"[expander] Similarity search failed (non-fatal): {e}")
        similar_topics = []   # continues without cross-curriculum context
```

#### Return shape (when populated)

```python
[
    {
        "topic": "Linear Algebra",            # query topic that matched
        "matched_subtopic": "Matrix Operations and Linear Systems",
        "course_code": "MAT1001",
        "course_name": "Engineering Mathematics I",
        "similarity_score": 0.91,
        "coverage_level": "intermediate",     # from subtopic.depth_level
        "unit_name": "Unit 3: Linear Systems"
    }
]
```

Results are injected into the expander context under:
`## Topics Already Covered in Prerequisite Courses (Avoid Duplication)`

**Wire-up needed in `dependencies.py` when Qdrant is ready:**
```python
def get_tool_runner() -> ToolRunner:
    # currently: raise NotImplementedError("MCPToolRunner not built yet")
    # replace with:
    from mcp.qdrant_mcp.server import run_similarity_search
    class MCPToolRunnerAdapter(ToolRunner):
        def run_similarity_search(self, topics, top_k=5):
            return run_similarity_search(topics, top_k)
    return MCPToolRunnerAdapter()
```

**What breaks if wrong:**
- False positives (says topic is covered when not) → Expander omits important topics → coverage gaps
- False negatives (misses overlap) → Expander duplicates prerequisite content
- `ConnectionError` → **NON-FATAL by design** — caught in expander, treated as empty result, Phase 1 continues

---

### `mcp/reference_database_mcp/`
**Status: ✅ Fully stubbed — all three operations defined**

**Connects to:** Internal reference DB with accreditation standards and benchmark curricula

**Type:** TOOL (always called by Phase 2 Relevance Evaluator; optionally called by Phase 3 CO agent)

#### Operations

| Function | Signature | Phase | Always/Optional |
|---|---|---|---|
| `lookup_benchmark_curriculum(domain, level, top_k)` | `str, str, int → dict` | 2 — Relevance Evaluator | Always |
| `lookup_accreditation_standards(domain, level, body)` | `str, str, str → dict` | 2 — Relevance Evaluator | Always |
| `lookup_co_frameworks(domain, body)` | `str, str → dict` | 3 — CO agent | Optional (agent decides) |

#### How Phase 2 uses it

```python
# In relevance_evaluator_node():
benchmarks = ref_tool.lookup_benchmark_curriculum(
    domain=state.syllabus_draft.course_metadata.domain,   # "Computer Science"
    level=state.syllabus_draft.course_metadata.course_level   # "UG"
)
# benchmarks["consensus_topics"] → topics in ≥2 benchmarks
# benchmarks["rarely_included"] → topics in draft but uncommon in benchmarks

standards = ref_tool.lookup_accreditation_standards(
    domain="Computer Science", level="UG", accreditation_body="NBA"
)
# standards["mandatory_topics"] → any missing = automatic fail
# standards["recommended_topics"] → missing = lower score, not automatic fail
```

**Graceful degradation:** If `LookupError` (domain not in DB) or `ConnectionError`, Relevance Evaluator marks itself `"skipped"` and logs a warning. A skipped evaluator is treated as a conditional pass — it does NOT block an otherwise-passing syllabus.

**What breaks if wrong:**
- Empty benchmark data → Relevance Evaluator has nothing to compare. Evaluates blindly.
- Wrong mandatory topics → False pass (missing required content) or false fail (correct syllabus rejected)
- `ConnectionError` unhandled → crashes evaluator node → entire Phase 2 fan-out fails for that course

---

### `mcp/document_generation_mcp/`
**Status: ✅ Fully stubbed — both operations defined (was 0 bytes before this session)**

**Connects to:** python-pptx rendering service + pandoc/WeasyPrint for PDF

**Type:** Always-called (Phase 5a/5b output writers always render to files)

#### Operations

| Function | Signature | Phase | What it produces |
|---|---|---|---|
| `render_pptx(slide_data, course_code, lecture_number, template_path)` | `list[dict], str, int → bytes` | 5a | Raw PPTX bytes. Caller stores via `filesystem_mcp.write_file()`. |
| `render_notes(notes_data, course_code, lecture_number)` | `dict, str, int → dict` | 5b | `{"md_bytes": bytes, "pdf_bytes": bytes}`. Caller stores both. |

**Important:** This server **only produces bytes**. It never writes to MinIO itself. The Phase 5a/5b output writer nodes call `document_generation_mcp.render_*()` to get bytes, then pass those bytes to `filesystem_mcp.write_file()` to store. Two separate concerns, two separate MCP servers.

---

### `mcp/quality_plagiarism_mcp/`
**Status: ✅ Fully stubbed — both operations defined (was 0 bytes before this session)**

**Connects to:** LLM-based quality scorer + external plagiarism API (Copyleaks or custom)

**Type:** Always-called (Phase 5b QA gate always runs both checks)

#### Operations

| Function | Signature | On fail |
|---|---|---|
| `check_quality(assembled_notes, lecture_plan_entry)` | `dict, dict → dict` | Failing subtopics get individually regenerated (targeted, not full redo) |
| `check_originality(text_block, course_code, lecture_number)` | `str, str, int → dict` | Flagged sections go to human review — NOT auto-regenerated |

#### Return shapes

**check_quality:**
```python
{
    "pass": bool,
    "quality_score": float,           # 0.0–1.0
    "failing_subtopics": [str],       # names to regenerate individually
    "missing_subtopics": [str],       # in plan but absent from notes entirely
    "subtopic_scores": { "name": {"covered": bool, "depth_score": float} },
    "overall_feedback": str
}
```

**check_originality:**
```python
{
    "pass": bool,
    "originality_score": float,       # 1.0 = fully original
    "flagged_sections": [
        {"text_excerpt": str, "similarity_pct": float, "source_reference": str}
    ],
    "requires_human_review": bool,
    "audit_id": str
}
```

**`ConnectionError` on `check_originality`** → mark originality as `"skipped"`, log warning, do NOT block notes output. Same graceful degradation pattern as Reference DB MCP.

---

## Current Build Status Summary

| Resource | File | Status |
|---|---|---|
| Academic Level Calibrator | `skills/knowledge/academic_level_calibrator.md` | ✅ Populated |
| Curriculum Parser Instructions | `skills/knowledge/curriculum_parser_instructions.md` | ✅ Populated |
| Bloom's Taxonomy | `skills/knowledge/blooms_taxonomy.md` | 🔲 Empty |
| CO Writing Guidelines | `skills/knowledge/co_writing_guidelines.md` | 🔲 Empty |
| Slide Structure | `skills/knowledge/slide_structure.md` | 🔲 Empty |
| Continuity Guidelines | `skills/knowledge/continuity_guidelines.md` | 🔲 Empty |
| File System MCP | `mcp/filesystem_mcp/server.py` | ✅ Stubbed (NotImplementedError) |
| PostgreSQL MCP | `mcp/postgresql_mcp/server.py` | ✅ Stubbed (NotImplementedError) |
| Qdrant MCP | `mcp/qdrant_mcp/server.py` | ✅ Stubbed (NotImplementedError) |
| Reference Database MCP | `mcp/reference_database_mcp/server.py` | ✅ Stubbed (NotImplementedError) |
| Document Generation MCP | `mcp/document_generation_mcp/server.py` | ✅ Stubbed (NotImplementedError) |
| Quality/Plagiarism MCP | `mcp/quality_plagiarism_mcp/server.py` | ✅ Stubbed (NotImplementedError) |
| Custom Tools MCP | `mcp/custom_tools_mcp/` | ❌ Not yet created |

> **Note on stubs:** All MCP servers correctly raise `NotImplementedError` in their functions. This is intentional — mock mode (via `dependencies.py`) bypasses them entirely. Real implementations get added inside the functions when the corresponding infrastructure (MinIO, PostgreSQL, Qdrant, etc.) is provisioned. No node or graph code changes when switching from mock to real.

---

## What `custom_tools_mcp` Needs to Be (Not Yet Built)

This MCP is needed for Phase 2 (Hours Evaluator) and Phase 5a (Image/Diagram Search):

| Function | Used by | What it does |
|---|---|---|
| `check_credit_hours(total_hours, credit_hours, tolerance_pct)` | Phase 2 Hours Evaluator | Arithmetic: is total_hours within ±tolerance% of credit_hours × 15? Returns `{within_range, expected_hours, actual_hours, deviation_pct}` |
| `search_diagrams(concept)` | Phase 5a slide content agents | Returns diagram/image references for a concept. Agent decides whether to call. |

---

## Dependency Injection — How Mock ↔ Real Switching Works

All of this is controlled by one env var: `DEPENDENCY_MODE=mock` or `DEPENDENCY_MODE=real`

The switch lives exclusively in each phase's `dependencies.py`. **Zero node or graph code changes** when switching.

```
DEPENDENCY_MODE=mock                    DEPENDENCY_MODE=real
─────────────────────────────────────   ─────────────────────────────────────
MockFileReader  → reads test_data/      MCPFileReaderAdapter  → filesystem_mcp
MockSkillLoader → reads skills/knowledge/ MCPSkillLoaderAdapter → filesystem_mcp
MockDBWriter    → writes mock_outputs/  MCPDBWriterAdapter   → postgresql_mcp
MockToolRunner  → returns []            MCPToolRunnerAdapter → qdrant_mcp
                                        MCPRefToolRunner     → reference_database_mcp
                                        MCPCalculatorTool    → custom_tools_mcp (TBD)
```

Phase 1's `dependencies.py` already has the real-mode MCP adapters wired as inline classes for File System and PostgreSQL. The Qdrant adapter still needs to be added when Qdrant is provisioned (see `qdrant_mcp/server.py` TODO comments for the exact code).
