# Phase 1 — Skills and MCP Usage Reference

## Scope of This Document

This document describes exactly how every skill file and every MCP server is used within Phase 1 (Curriculum to Syllabus Expansion). It answers three questions for each resource:

1. **Which node uses it** — where in the graph does it get called
2. **How it is used** — skill injection vs tool call vs read/write operation
3. **What breaks if it is wrong** — the downstream consequence of a bad skill or a bad MCP response

Read this before touching any skill file or MCP server implementation. Every decision here is intentional.

---

## Phase 1 Graph — Node Execution Order

```
curriculum_loader
      │
      ▼
skill_injector
      │
      ▼
   expander ◄──────────────────────┐
      │                            │
      ▼                            │
  gap_critic                       │
      │                            │
      ▼                   iteration_counter
    router ────(gaps + iter < max)──┘
      │
      └──(no gaps OR iter >= max)──►  output_writer ──► END
```

The graph has two distinct phases of life:
- **Entry sequence** (runs once): `curriculum_loader` → `skill_injector`
- **Cyclic core** (runs 1–3 times): `expander` → `gap_critic` → `router` → (optionally back to `expander`)
- **Exit** (runs once): `output_writer`

---

## Skills Used in Phase 1

Skills are **not tools**. They are not called during reasoning. They are markdown files loaded into state **once** by `skill_injector` and then passed as raw text inside the LLM prompt for every subsequent node that needs them. The agent reads them like a reference manual before it starts thinking.

---

### Skill 1 — `academic_level_calibrator.md`

**File path:** `skills/knowledge/academic_level_calibrator.md`

**Loaded by:** `skill_injector` node — stored in `state.level_calibrator_skill`

**Used in state field:** `Phase1State.level_calibrator_skill: str`

#### Which nodes consume it

| Node | How it is used |
|---|---|
| `expander` | Injected into the user context via `_build_expander_context()`. The expander reads it to decide how deeply to expand each subtopic and what `depth_level` and `estimated_hours` are appropriate for the stated `course_level`. |
| `gap_critic` | Injected into the critic context via `_build_critic_context()`. The critic uses it to evaluate whether the expander's depth choices are correct for the stated level. Gap type `depth_mismatch` is entirely driven by this skill. |

#### What the expander does with it

Before generating the `SyllabusDraft`, the expander receives a block in its context that looks like:

```
## Academic Level Calibrator Skill
# Academic Level Calibrator Skill
...
### Undergraduate (UG)
- Depth: Conceptual understanding with practical application...
- Estimated subtopic hours: 1–3 hours per subtopic
...
```

The expander uses this to:
- Set `depth_level` on each `Subtopic` (`"introductory"` / `"intermediate"` / `"advanced"`)
- Set `estimated_hours` per subtopic within the level's range
- Write `description` fields at the right cognitive complexity
- Avoid assuming prior knowledge not appropriate for the level

#### What the critic does with it

The critic receives the same skill in its context, then checks the `SyllabusDraft` JSON against it. It produces `depth_mismatch` gaps when:
- A UG subtopic has `estimated_hours > 4` without clear justification
- A PhD subtopic is described as `"introductory"` depth
- A UG description uses research-paper vocabulary without explanation
- PG content re-teaches basics that should be assumed

#### What breaks if this skill is wrong

- **Bad depth level rules** → expander produces subtopics that are too shallow (UG content treated as PhD) or too deep (UG content written like a research seminar). Phase 2's Level Evaluator will catch this, but it wastes an iteration cycle.
- **Wrong hour estimates** → total hours across the syllabus will fall outside the credit-hour range. Phase 2's Hours Evaluator will fail the syllabus.
- **Missing level definition** → if a course is `PG` but the skill has no PG section, the LLM falls back to general knowledge and produces inconsistent depth.

---

### Skill 2 — `curriculum_parser_instructions.md`

**File path:** `skills/knowledge/curriculum_parser_instructions.md`

**Loaded by:** `skill_injector` node — stored in `state.parser_instructions_skill`

**Used in state field:** `Phase1State.parser_instructions_skill: str`

#### Which nodes consume it

| Node | How it is used |
|---|---|
| `curriculum_loader` | **Not directly** — the `curriculum_loader` node uses its own inline extraction prompt. The parser instructions skill is loaded into state for the **expander** to refer to when it interprets the raw curriculum. |
| `expander` | Available in state. The expander uses it implicitly when deciding what to do with vague entries, flat topic lists, or ambiguous abbreviations in the raw curriculum text. |

#### Why it is loaded even though `curriculum_loader` has its own prompt

The `curriculum_loader` uses a short, hardcoded extraction prompt to get `CourseMetadata`. That prompt handles the easy cases. The skill is richer and covers edge cases (flat lists, abbreviations, duplicates, vague entries like "Advanced Topics") that the expander needs to handle during expansion, not during metadata extraction.

The separation is intentional:
- `curriculum_loader` → extracts `CourseMetadata` fields (structured, deterministic)
- `expander` → uses parser instructions to correctly interpret the raw topic list during expansion (contextual, needs guidance)

#### What the expander does with it

When the raw curriculum has:
- Roman numeral units → expander knows to treat `Unit III` as `unit_number: 3`
- Flat topic list with no units → expander groups them logically (as the skill instructs)
- `"Advanced Topics"` entry → expander flags it as needing expansion and handles it specially
- Abbreviation `"ML"` → expander expands to "Machine Learning" in subtopic names

#### What breaks if this skill is wrong

- **Missing flat-list grouping rules** → expander creates arbitrary unit groupings that do not make pedagogical sense. The Gap Critic (sequencing_issue) catches this, but costs an iteration.
- **Wrong abbreviation handling** → subtopic names have inconsistent terminology. Downstream phases (Phase 5a slide outline agent) inherit these names and produce inconsistent slide titles.
- **No vague-entry guidance** → the expander either skips "Advanced Topics" entirely (coverage gap) or over-expands it into made-up content (hallucination). The critic will flag the coverage gap but cannot catch hallucinated content reliably.

---

## MCP Servers Used in Phase 1

MCP servers are the connection layer between the graph and external systems. Unlike skills, MCP calls happen at specific points in specific nodes — they are not injected into prompts. The graph calls them to read data in and write data out.

Phase 1 uses two MCP servers: **File System MCP** and **PostgreSQL MCP**.

---

### MCP 1 — File System MCP

**Server file:** `mcp/filesystem_mcp/server.py`

**Interface used:** `interfaces/file_reader.py` and `interfaces/skill_loader.py` (in Phase 1)

**In mock mode:** `MockFileReader` (reads from `test_data/`) + `MockSkillLoader` (reads from `phase1/skills/`)

**In production:** `MCPFileReader` and `MCPSkillLoader` (reads from MinIO buckets)

#### Operations called in Phase 1

| Operation | Called by node | What it does |
|---|---|---|
| `read_curriculum(file_path)` | `curriculum_loader` | Retrieves the raw curriculum MD or PDF from MinIO. Returns full plain text. |
| `read_skill("academic_level_calibrator.md")` | `skill_injector` | Reads the skill file from the skills bucket. Returns markdown string. |
| `read_skill("curriculum_parser_instructions.md")` | `skill_injector` | Same — reads the second skill file. |

**Note:** `write_file()` and `list_skills()` are NOT used in Phase 1. They are Phase 5a/5b operations.

#### `curriculum_loader` — File System MCP call detail

```python
# Inside curriculum_loader_node():
file_reader = get_file_reader()                              # → MockFileReader or MCPFileReader
curriculum_text = file_reader.read_curriculum(              # MCP call
    state.curriculum_file_path                              # e.g. "cs/CSE2001_curriculum.md"
)
# curriculum_text is then stored in state.curriculum_raw
```

The call must return a clean plain-text string. If the source is a PDF, the MCP server is responsible for extracting text before returning — not the node.

#### `skill_injector` — File System MCP call detail

```python
# Inside skill_injector_node():
skill_loader = get_skill_loader()                           # → MockSkillLoader or MCPSkillLoader
level_calibrator = skill_loader.load(                      # MCP call 1
    "academic_level_calibrator.md"
)
parser_instructions = skill_loader.load(                   # MCP call 2
    "curriculum_parser_instructions.md"
)
# Both stored in state as plain markdown strings
```

Skills are loaded **once** at graph entry. They are NOT reloaded between iterations. If you update a skill file mid-run, the current run will not see the change — only the next run will.

#### What breaks if the File System MCP is wrong

| Problem | Consequence |
|---|---|
| `read_curriculum` returns empty string | `curriculum_loader` produces minimal fallback `CourseMetadata`. Expander has nothing to expand. Graph force-passes with a skeleton syllabus. |
| `read_curriculum` raises `FileNotFoundError` | Graph crashes at node 1. Pipeline fails for this course code. |
| `read_skill` returns empty string | Skill field in state is empty. Expander and critic receive a blank skill block. LLM falls back to general knowledge — depth calibration quality degrades significantly. |
| `read_skill` raises `FileNotFoundError` | `skill_injector` crashes. Entire phase fails. All downstream phases blocked. |
| PDF extraction is garbage | Raw text is garbled. LLM extracts wrong metadata and topic names. Entire downstream is built on bad input. |

---

### MCP 2 — PostgreSQL MCP

**Server file:** `mcp/postgresql_mcp/server.py`

**Interface used:** `interfaces/db_writer.py` (in Phase 1)

**In mock mode:** `MockDBWriter` (writes JSON files to `mock_outputs/`)

**In production:** `MCPPostgresWriter` (writes to `syllabuses` table in PostgreSQL)

#### Operations called in Phase 1

| Operation | Called by node | What it does |
|---|---|---|
| `check_syllabus_exists(course_code)` | `curriculum_loader` (pre-check) | Prevents reprocessing a course that was already expanded. Returns `True` if a record exists. |
| `write_syllabus(syllabus, course_code, phase_status, iteration_count)` | `output_writer` | Persists the final `SyllabusDraft` JSON, status, and iteration metadata. Returns a `record_id`. |

**Note:** `read_syllabus()`, `write_refined_syllabus()`, and all other operations are Phase 2+ only. Phase 1 only writes — it never reads from a previous phase because it IS the first phase.

#### `output_writer` — PostgreSQL MCP call detail

```python
# Inside output_writer_node():
db_writer = get_db_writer()                                # → MockDBWriter or MCPPostgresWriter

record_id = db_writer.write_syllabus(
    syllabus=state.syllabus_draft,                         # SyllabusDraft Pydantic model
    course_code=state.course_metadata.course_code,         # e.g. "CSE2001"
    phase_status=phase_status,                             # "passed" or "force_passed"
    iteration_count=state.iteration_count                  # 0, 1, or 2
)
```

The `write_syllabus` call must be the **last thing** that happens in Phase 1. It signals to Phase 2 that this course's syllabus is available to read. If this call fails, Phase 2 will find no record and cannot start.

#### What the written record contains

```json
{
  "record_id": "CSE2001_20260419_114500",
  "course_code": "CSE2001",
  "phase_status": "passed",
  "iteration_count": 1,
  "written_at": "2026-04-19T11:45:00",
  "syllabus": {
    "course_metadata": { ... },
    "topics": [ ... ],
    "total_hours": 60.0,
    "coverage_summary": "..."
  }
}
```

In mock mode (`MockDBWriter`), this is written to `phase1/mock_outputs/syllabus_CSE2001_<timestamp>.json`.  
In production, this is a row in the `syllabuses` table with `syllabus` stored as JSONB.

#### What breaks if the PostgreSQL MCP is wrong

| Problem | Consequence |
|---|---|
| `write_syllabus` raises `ConnectionError` | `output_writer` returns `phase_status: "failed"`. Phase 2 has no input. The course is stuck. |
| `write_syllabus` writes malformed JSONB | Phase 2's `read_syllabus` returns garbage. The four Phase 2 evaluators all fail on a corrupt SyllabusDraft. |
| `check_syllabus_exists` always returns `True` | Every course is skipped as "already processed". No new courses ever get expanded. |
| `check_syllabus_exists` always returns `False` | Every course is reprocessed even if it was already done. Wasted compute on 200+ courses. |
| `record_id` returned is not unique | Audit trail is broken. You cannot tell which run produced which syllabus. |

---

## Qdrant MCP — Optional Tool in Phase 1

**Server file:** (not yet created — this is the `qdrant_mcp` server)

**Interface used:** `interfaces/tool_runner.py`

**In mock mode:** `MockToolRunner` — always returns `[]` (empty list)

**This is a tool, not a skill.** The expander decides at runtime whether to call it.

#### When the expander calls it

```python
# Inside expander_node():
if state.course_metadata and state.course_metadata.prerequisites:
    similar_topics = tool_runner.run_similarity_search(
        topics=[curriculum_words],
        top_k=5
    )
```

The call only happens when the course has listed prerequisites. If `prerequisites` is empty, the tool is never called.

#### What it returns

```python
[
    {
        "topic": "Linear Algebra",
        "course_code": "MAT1001",
        "course_name": "Engineering Mathematics I",
        "similarity_score": 0.92,
        "coverage_level": "intermediate"
    },
    ...
]
```

The expander uses these results to avoid re-expanding topics that are already deeply covered in a prerequisite course. The results are injected into the expander context under:
```
## Topics Already Covered in Prerequisite Courses (Avoid Duplication)
```

#### What breaks if this tool is wrong

| Problem | Consequence |
|---|---|
| Returns false positives (says a topic is covered when it is not) | Expander omits important topics. Coverage gaps appear. Critic flags them. |
| Returns false negatives (misses overlap) | Expander duplicates prerequisite content. Not caught by Phase 1 critic — only caught if Phase 2 Relevance Evaluator compares against prerequisites. |
| Raises `ConnectionError` | Caught gracefully in `expander_node`. Treated as empty result — similarity search is skipped. Graph continues normally. |

The Qdrant tool failure is **non-fatal by design**. The `try/except` in `expander_node` catches connection errors and continues with `similar_topics = []`. This is intentional — the tool improves quality but is not required for correctness.

---

## Dependency Mode Reference

All three dependencies (File System MCP, PostgreSQL MCP, Qdrant MCP) are controlled by a single environment variable:

```
DEPENDENCY_MODE=mock    # development — no infrastructure needed
DEPENDENCY_MODE=real    # production — all MCP servers must be running
```

The factory functions in `dependencies.py` are the **only** place this switch lives:

```python
def get_file_reader() -> FileReader:
    if config.DEPENDENCY_MODE == "mock":
        return MockFileReader()
    else:
        return MCPFileReader()        # implement when MinIO is ready

def get_db_writer() -> DBWriter:
    if config.DEPENDENCY_MODE == "mock":
        return MockDBWriter()
    else:
        return MCPPostgresWriter()    # implement when PostgreSQL is ready

def get_tool_runner() -> ToolRunner:
    if config.DEPENDENCY_MODE == "mock":
        return MockToolRunner()
    else:
        return MCPToolRunner()        # implement when Qdrant is ready
```

**No node or graph code changes when switching from mock to real.** Only `dependencies.py` changes.

---

## Summary Table — Phase 1 Resource Map

| Resource | Type | Loaded/Called by | When in graph | State field / return |
|---|---|---|---|---|
| `academic_level_calibrator.md` | Skill (MD) | `skill_injector` | Entry — once | `state.level_calibrator_skill` |
| `curriculum_parser_instructions.md` | Skill (MD) | `skill_injector` | Entry — once | `state.parser_instructions_skill` |
| `read_curriculum()` | File System MCP | `curriculum_loader` | Entry — once | `state.curriculum_raw` |
| `read_skill(x2)` | File System MCP | `skill_injector` | Entry — once | State skill fields |
| `run_similarity_search()` | Qdrant MCP (tool) | `expander` | Each iteration — conditional | `state.similar_topics_found` |
| `check_syllabus_exists()` | PostgreSQL MCP | `curriculum_loader` | Entry — once | (guards early exit) |
| `write_syllabus()` | PostgreSQL MCP | `output_writer` | Exit — once | Returns `record_id` |
