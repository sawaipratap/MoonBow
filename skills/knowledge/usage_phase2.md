# Phase 2 — Skills and MCP Usage Reference

## Scope of This Document

Phase 2 takes the `SyllabusDraft` written to PostgreSQL by Phase 1 and evaluates it across **four independent quality dimensions simultaneously**. It is implemented as a LangGraph graph with a fan-out/fan-in pattern: four evaluator nodes run in parallel, then an aggregator routes the result.

This document describes exactly how every skill and every MCP server is used within Phase 2. Same format as the Phase 1 usage doc.

---

## Phase 2 Graph — Node Execution Order

```
              skill_injector
                    │
                    ▼
              syllabus_reader ──── reads SyllabusDraft from PostgreSQL
                    │
                  fan-out (all four run in parallel)
          ┌─────────┬──────────┬──────────┐
          ▼         ▼          ▼          ▼
    level_eval  seq_eval  hours_eval  rel_eval
          └─────────┴──────────┴──────────┘
                    │
                 aggregator
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
  (all pass)            (any fail)
  write_refined         route back to Phase 1
  syllabus ──►          Expander with
  PostgreSQL            compiled feedback
```

Key structural differences from Phase 1:
- **No cycle within Phase 2.** If evaluators fail, feedback goes back to Phase 1's Expander — Phase 2 does not retry internally.
- **Parallel evaluation.** The four evaluator nodes are independent and run concurrently.
- **Skills load once** in `skill_injector`, then each evaluator node that needs a skill reads it from state.
- **Two MCP servers** are active: PostgreSQL MCP (reads Phase 1 output, writes Phase 2 output) and Reference Database MCP (queried by the Relevance Evaluator as a tool).

---

## Skills Used in Phase 2

Phase 2 uses **one skill**: `academic_level_calibrator.md`. The other three evaluators (Sequence, Hours, Relevance) do not require skill injection — their evaluation criteria are either self-contained or tool-driven.

---

### Skill — `academic_level_calibrator.md`

**File path:** `skills/knowledge/academic_level_calibrator.md`

**Loaded by:** `skill_injector` node — stored in `state.level_calibrator_skill`

**This is the same file used by Phase 1.** Phase 2 reads it from `skills/knowledge/` via the same `MockSkillLoader` / `MCPSkillLoader` pattern.

#### Which node consumes it

| Node | How it is used |
|---|---|
| `level_evaluator` | The only Phase 2 node that uses a skill. Injected into the evaluator's prompt as a reference for judging whether the syllabus depth, vocabulary, and hour allocations match the stated `course_level`. |

#### What the Level Evaluator does with it

The Level Evaluator receives the full `SyllabusDraft` JSON and the `academic_level_calibrator.md` content. It runs a structured evaluation:

1. **Depth check:** For each subtopic, does the `depth_level` field (`"introductory"` / `"intermediate"` / `"advanced"`) match what the skill specifies for the course level? A UG course should have mostly `introductory`–`intermediate` subtopics; a PhD course should have mostly `intermediate`–`advanced`.
2. **Hour check (level appropriateness):** Are the `estimated_hours` per subtopic within the ranges the skill defines? (UG: 1–3h, PG: 2–5h, PhD: 3–8h). The Hours Evaluator handles total credit compliance; the Level Evaluator handles per-subtopic hour calibration.
3. **Description vocabulary check:** Reads the `description` field of each subtopic and evaluates whether the language, concepts referenced, and assumed prior knowledge are appropriate for the level.
4. **Prior knowledge assumption check:** Flags descriptions that assume knowledge not available to a student at this level, based on the skill's "Expected prior knowledge" sections.

The evaluator returns:
```json
{
  "evaluator": "level",
  "pass": true | false,
  "score": 0.0–1.0,
  "feedback": "Specific description of what is wrong and where",
  "failing_subtopics": ["subtopic_name_1", "subtopic_name_2"]
}
```

#### What breaks if this skill is wrong

| Problem | Consequence |
|---|---|
| Wrong hour ranges for a level | Level Evaluator flags technically correct subtopics as depth mismatches. Phase 1 gets false-positive feedback and wastes a rewrite cycle. |
| Missing a level section (e.g., no PhD section) | LLM falls back to general knowledge. Level Evaluator becomes unreliable for PhD courses. |
| Vocabulary expectation too strict | Over-flags UG descriptions that are appropriately foundational as "too shallow", creating unnecessary rework. |
| Vocabulary expectation too loose | Misses genuinely miscalibrated content, letting depth errors through to Phase 3. |

---

## MCP Servers Used in Phase 2

Phase 2 uses two MCP servers: **PostgreSQL MCP** (reads Phase 1 output, writes Phase 2 output) and **Reference Database MCP** (queried as a tool by the Relevance Evaluator).

---

### MCP 1 — PostgreSQL MCP

**Server file:** `mcp/postgresql_mcp/server.py`

**Operations called in Phase 2:**

| Operation | Called by node | What it does |
|---|---|---|
| `read_syllabus(course_code)` | `syllabus_reader` | Reads the `SyllabusDraft` written by Phase 1 from the `syllabuses` table. |
| `write_refined_syllabus(syllabus, course_code, evaluation_results)` | `output_writer` | Writes the approved `RefinedSyllabus` to the `refined_syllabuses` table alongside all four evaluator results. |

**Note:** `check_syllabus_exists`, `write_syllabus`, and all Phase 3+ operations are NOT used in Phase 2.

#### `syllabus_reader` — PostgreSQL MCP call detail

```python
# Inside syllabus_reader_node():
db_reader = get_db_reader()
syllabus_dict = db_reader.read_syllabus(
    course_code=state.course_code     # e.g. "MATH2059"
)
syllabus_draft = SyllabusDraft(**syllabus_dict["syllabus"])
```

This is the **first node that runs** in Phase 2 (after skill injection). It retrieves the exact JSON structure that `MockDBWriter.write_syllabus()` or `MCPPostgresWriter.write_syllabus()` stored in Phase 1. The `phase_status` field in that record is checked — if it is `"failed"`, Phase 2 should not proceed.

The data shape coming in from Phase 1 (confirmed from `mock_outputs/`):
```json
{
  "record_id": "mock_MATH2059_20260419_123542",
  "course_code": "MATH2059",
  "phase_status": "passed",
  "iteration_count": 2,
  "syllabus": {
    "course_metadata": { "course_level": "UG", "credit_hours": 3, ... },
    "topics": [ { "unit_number": 1, "subtopics": [...], "total_hours": float, ... } ],
    "total_hours": 45.0,
    "coverage_summary": "..."
  }
}
```

#### `output_writer` — PostgreSQL MCP call detail

```python
# Inside output_writer_node():
db_writer = get_db_writer()
record_id = db_writer.write_refined_syllabus(
    syllabus=state.syllabus_draft,             # same SyllabusDraft (possibly unchanged)
    course_code=state.course_code,
    evaluation_results={                        # all four evaluator outputs
        "level": state.level_eval_result,
        "sequence": state.sequence_eval_result,
        "hours": state.hours_eval_result,
        "relevance": state.relevance_eval_result
    }
)
```

This write only happens when **all four evaluators pass**. If any fail, the aggregator routes back to Phase 1 instead of calling this. Phase 3 reads from the `refined_syllabuses` table — if this write never happens, Phase 3 cannot start.

#### What breaks if the PostgreSQL MCP is wrong

| Problem | Consequence |
|---|---|
| `read_syllabus` returns Phase 1 `phase_status: "failed"` record | Phase 2 proceeds on a broken syllabus. All four evaluators will likely fail. The feedback sent to Phase 1 will be noisy and unhelpful. |
| `read_syllabus` returns data with wrong `total_hours` | Hours Evaluator produces wrong result. May pass a syllabus that is actually out of budget. |
| `write_refined_syllabus` silently drops `evaluation_results` | Audit trail is broken. Phase 3 and human reviewers cannot see which evaluators passed or what feedback was given. |
| `write_refined_syllabus` fails | Phase 3 has no input. One successful phase write failure blocks all downstream phases for this course. |

---

### MCP 2 — Reference Database MCP

**Server file:** `mcp/reference_database_mcp/server.py`

**This is a TOOL, not a skill.** Unlike the PostgreSQL MCP (which is always called), the Relevance Evaluator calls the Reference Database MCP as part of its **fixed evaluation logic** — it always queries this server. But Phase 2 is the only fixed caller; in Phase 3 the same server is used as an agent-decided optional tool.

**In mock mode:** The `MockToolRunner` returns empty/stub reference data so the Relevance Evaluator can still produce an evaluation output.

**In production:** Connects to the internal Reference DB with curated NBA/NAAC standards and benchmark curricula.

#### Operations called in Phase 2

| Operation | Called by node | What it does |
|---|---|---|
| `lookup_benchmark_curriculum(domain, level, top_k=3)` | `relevance_evaluator` | Returns benchmark course topic lists from 3 leading institutions for this domain/level. Used to identify missing or outdated topics. |
| `lookup_accreditation_standards(domain, level)` | `relevance_evaluator` | Returns NBA/NAAC mandatory and recommended topic lists and credit-hour norms for this domain/level. |

#### `relevance_evaluator` — Reference Database MCP call detail

```python
# Inside relevance_evaluator_node():
ref_tool = get_ref_tool_runner()

benchmarks = ref_tool.lookup_benchmark_curriculum(
    domain=state.syllabus_draft.course_metadata.domain,   # e.g. "Computer Science"
    level=state.syllabus_draft.course_metadata.course_level,  # "UG"
    top_k=3
)

standards = ref_tool.lookup_accreditation_standards(
    domain=state.syllabus_draft.course_metadata.domain,
    level=state.syllabus_draft.course_metadata.course_level,
    accreditation_body="NBA"    # configured per institution
)
```

The evaluator then:
1. Compares the `topics` in the `SyllabusDraft` against `benchmarks["consensus_topics"]` — topics that appear in ≥2 benchmark curricula and are absent from the draft get flagged.
2. Checks `standards["mandatory_topics"]` — any topic marked mandatory by the accreditation body that is missing is an automatic fail.
3. Checks `standards["recommended_topics"]` — missing recommended topics contribute to a lower relevance score but do not automatically fail.
4. Looks for topics in the draft that appear in `benchmarks["rarely_included"]` — signals potentially non-standard content worth noting.

The evaluator returns:
```json
{
  "evaluator": "relevance",
  "pass": true | false,
  "score": 0.0–1.0,
  "feedback": "Specific description of what is outdated or missing vs benchmarks",
  "missing_mandatory_topics": ["topic_1"],
  "missing_recommended_topics": ["topic_2", "topic_3"],
  "non_standard_topics": ["topic_4"]
}
```

#### `hours_evaluator` — Custom Tools MCP call detail

The Hours Evaluator also calls an external tool — the **Credit Hour Calculator** from `custom_tools_mcp`. This is arithmetic, not a DB lookup:

```python
# Inside hours_evaluator_node():
calculator = get_calculator_tool()

result = calculator.check_credit_hours(
    total_estimated_hours=state.syllabus_draft.total_hours,
    credit_hours=state.syllabus_draft.course_metadata.credit_hours,
    tolerance_pct=10.0          # ±10% is acceptable (from the expander prompt rule)
)
# result: {"within_range": bool, "expected_hours": float, "actual_hours": float, "deviation_pct": float}
```

The Hours Evaluator also checks **distribution across units** — no single unit should consume more than 40% of total hours without justification. This distribution check is done by the LLM using the syllabus data, not by the calculator tool.

#### What breaks if the Reference Database MCP is wrong

| Problem | Consequence |
|---|---|
| `lookup_benchmark_curriculum` returns empty benchmarks | Relevance Evaluator has no reference to compare against. It either passes everything (uninformative) or flags everything (noisy). Either way, the evaluation is useless. |
| `lookup_accreditation_standards` returns wrong mandatory topics | The evaluator may pass a syllabus missing required content (false pass) or fail a correct syllabus (false fail). Both are harmful at scale across 200+ courses. |
| Domain not found in Reference DB | Raises `LookupError`. Must be caught by the evaluator node — on lookup failure, the Relevance Evaluator should log a warning and mark itself as `"skipped"` rather than crashing the entire evaluator suite. |
| Reference DB is unreachable | `ConnectionError`. Same graceful degradation: mark Relevance Evaluator as `"skipped"`, proceed with the other three evaluators' results. A skipped evaluator should not block an otherwise passing syllabuses. |

---

## The Four Evaluators — What Each Needs

| Evaluator | Skill used | MCP tool called | Evaluation axis |
|---|---|---|---|
| `level_evaluator` | `academic_level_calibrator.md` | None | Is depth/vocabulary/hours calibrated to course level? |
| `sequence_evaluator` | None | None | Is topic ordering pedagogically sound? (LLM-only reasoning) |
| `hours_evaluator` | None | Credit Hour Calculator (custom_tools_mcp) | Is total hours within ±10% of credit hours? Is distribution reasonable? |
| `relevance_evaluator` | None | `lookup_benchmark_curriculum` + `lookup_accreditation_standards` (reference_database_mcp) | Is content current, complete, and aligned with accreditation standards? |

The Sequence Evaluator is the only evaluator that uses **neither a skill nor a tool** — its evaluation is pure LLM reasoning over the topic ordering in the `SyllabusDraft`. It looks for cases where a later unit assumes concepts introduced even later, foundational concepts after advanced applications, or illogical difficulty jumps.

---

## Aggregator Logic

After all four evaluators complete, the aggregator node receives all four results from state and makes the routing decision:

```python
all_pass = all([
    state.level_eval_result["pass"],
    state.sequence_eval_result["pass"],
    state.hours_eval_result["pass"],
    state.relevance_eval_result["pass"]  # or "skipped" counts as conditional pass
])

if all_pass:
    → write_refined_syllabus to PostgreSQL
    → Phase 3 can start
else:
    failing_feedback = compile([
        eval["feedback"] for eval in results if not eval["pass"]
    ])
    → route back to Phase 1 Expander with failing_feedback
    → Phase 1 re-runs with targeted instructions
```

A `"skipped"` evaluator (due to Reference DB unavailability) is treated as a **conditional pass** with a warning logged. The rationale: a missing reference lookup should not block course processing at scale — it means one quality dimension was not checked, not that the content is bad.

---

## Dependency Mode Reference

Same pattern as Phase 1. Controlled by `DEPENDENCY_MODE` environment variable:

```python
# phase2/dependencies.py (to be created by the phase2 developer)

def get_skill_loader() -> SkillLoader:
    if config.DEPENDENCY_MODE == "mock":
        return MockSkillLoader()        # reads from skills/knowledge/
    return MCPSkillLoader()             # reads from MinIO via filesystem_mcp

def get_db_reader() -> DBReader:
    if config.DEPENDENCY_MODE == "mock":
        return MockDBReader()           # reads from phase1/mock_outputs/
    return MCPPostgresReader()          # reads from syllabuses table

def get_db_writer() -> DBWriter:
    if config.DEPENDENCY_MODE == "mock":
        return MockDBWriter()           # writes to phase2/mock_outputs/
    return MCPPostgresWriter()          # writes to refined_syllabuses table

def get_ref_tool_runner() -> RefToolRunner:
    if config.DEPENDENCY_MODE == "mock":
        return MockRefToolRunner()      # returns stub benchmark/standards data
    return MCPRefToolRunner()           # calls reference_database_mcp.server functions

def get_calculator_tool() -> CalculatorTool:
    if config.DEPENDENCY_MODE == "mock":
        return MockCalculatorTool()     # does the arithmetic directly in Python
    return MCPCalculatorTool()          # calls custom_tools_mcp credit hour calculator
```

**No evaluator node or graph code changes when switching from mock to real.** Only `dependencies.py` changes.

---

## Summary Table — Phase 2 Resource Map

| Resource | Type | Loaded/Called by | When in graph | State field / return |
|---|---|---|---|---|
| `academic_level_calibrator.md` | Skill (MD) | `skill_injector` | Entry — once | `state.level_calibrator_skill` |
| `read_syllabus()` | PostgreSQL MCP | `syllabus_reader` | Entry — once | `state.syllabus_draft` |
| `lookup_benchmark_curriculum()` | Reference DB MCP (tool) | `relevance_evaluator` | Parallel eval phase | `state.relevance_eval_result` |
| `lookup_accreditation_standards()` | Reference DB MCP (tool) | `relevance_evaluator` | Parallel eval phase | `state.relevance_eval_result` |
| `check_credit_hours()` | Custom Tools MCP (tool) | `hours_evaluator` | Parallel eval phase | `state.hours_eval_result` |
| `write_refined_syllabus()` | PostgreSQL MCP | `output_writer` | Exit — once (all pass only) | Returns `record_id` |
