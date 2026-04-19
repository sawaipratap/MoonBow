# Educational Content Generation — Agentic Architecture

## System Purpose

An agentic pipeline that takes a raw course curriculum and produces:
- A refined, pedagogically sound syllabus
- Course Outcomes (COs) and Sub-COs mapped to Bloom's Taxonomy
- A lecture-wise content plan
- Generated PPTs per lecture
- Generated lecture notes per lecture (informed by PPT content)

Designed to process **200+ courses** running on **2 × DGX nodes (8 × H100 each)**.

---

## Overall Pipeline Flow

```mermaid
flowchart TD
    IN([Curriculum Input\nMD / PDF from MinIO]) --> P1

    subgraph P1["Phase 1 — Syllabus Expansion (LangGraph)"]
        EX[Expander Node] --> GC[Gap Critic Node]
        GC -->|Gaps Found — iteration < 3| EX
        GC -->|No Gaps / Max Iterations| S1[(Syllabus v1\nPostgreSQL)]
    end

    S1 --> P2

    subgraph P2["Phase 2 — Syllabus Refinement (LangGraph)"]
        direction TB
        S1R[Read Syllabus] --> LV[Level Evaluator]
        S1R --> SQ[Sequence Evaluator]
        S1R --> HR[Hours Evaluator]
        S1R --> RL[Relevance Evaluator]
        LV & SQ & HR & RL --> AG[Aggregator Node]
        AG -->|All Pass| S2[(Approved Syllabus\nPostgreSQL)]
        AG -->|Fail — with targeted feedback| EX
    end

    S2 --> P3

    subgraph P3["Phase 3 — Course Outcomes + Bloom's (PhiData)"]
        RA[ReAct Agent] -->|Consult| BT[(Bloom's Taxonomy\nMD Skill)]
        BT --> RA
        RA --> SC[Self-check Coverage]
        SC -->|Coverage OK| CO[(COs + Sub-COs\nJSON — PostgreSQL)]
        SC -->|Gaps| RA
    end

    CO --> P4

    subgraph P4["Phase 4 — Lecture-wise Planning (Direct LLM)"]
        LC[Single LLM Call\nStructured JSON Output] --> LP[(Lecture Plan Array\nPostgreSQL)]
    end

    LP --> P5A

    subgraph P5A["Phase 5a — PPT Generation (LangGraph) — Sequential per Lecture"]
        OA[Slide Outline Agent\nFull Lecture View] --> SA[Send API\nDynamic Fan-out]
        SA --> SL1[Slide 1 Agent]
        SA --> SL2[Slide 2 Agent]
        SA --> SL3[Slide 3 Agent]
        SA --> SLN[Slide N Agent]
        SL1 & SL2 & SL3 & SLN --> AS[Assembly +\nConsistency Node]
        AS --> PP[(PPTX\nMinIO)]
    end

    PP --> P5B

    subgraph P5B["Phase 5b — Notes Generation (LangGraph) — Sequential per Lecture"]
        NO[Notes Orchestrator\nReads PPT Content] --> SN[Send API\nDynamic Fan-out]
        SN --> ST1[Subtopic 1\nNotes Agent]
        SN --> ST2[Subtopic 2\nNotes Agent]
        SN --> ST3[Subtopic 3\nNotes Agent]
        SN --> STN[Subtopic N\nNotes Agent]
        ST1 & ST2 & ST3 & STN --> NA[Notes Assembler]
        NA --> QA{QA Gate\nQuality + Plagiarism}
        QA -->|Pass| NT[(Notes MD / PDF\nMinIO)]
        QA -->|Fail| TR[Targeted\nRegeneration]
        TR --> NA
    end
```

---

## Phase 1 — Syllabus Expansion

**Framework:** LangGraph
**Pattern:** Generator → Critic Cyclic Graph with Conditional Edge

### What Happens

The Expander takes the raw curriculum and produces a detailed structured syllabus with subtopics, depth indicators, and topic relationships. The Gap Critic evaluates it specifically for missing prerequisites, coverage gaps, and illogical sequencing — not for style or completeness in general. If gaps are found, it sends targeted feedback back to the Expander. Maximum 3 iterations, then force-pass.

### Skills Used
- `curriculum_parser.py` — parses raw MD/PDF curriculum into structured input
- `academic_level_calibrator.md` — ensures expansion depth matches course level (UG/PG/PhD)

### MCP Used
- **File System MCP** — reads curriculum from MinIO
- **PostgreSQL MCP** — writes approved syllabus

```mermaid
flowchart TD
    A([Curriculum MD/PDF]) -->|File System MCP| CP[curriculum_parser.py\nExtract structured topics]
    CP --> EX

    subgraph LG["LangGraph State Machine"]
        EX["Expander Node\nProduces subtopics, depth,\nprerequisites, relationships"]
        GC["Gap Critic Node\nChecks: missing prerequisites\ncoverage gaps, illogical sequencing"]
        CNT{Iteration < 3?}
        GAPS{Gaps Found?}

        EX --> GC
        GC --> GAPS
        GAPS -->|Yes| CNT
        CNT -->|Yes — feedback to Expander| EX
        CNT -->|No — force pass| OUT
        GAPS -->|No| OUT
    end

    OUT[Syllabus v1] -->|PostgreSQL MCP| DB[(PostgreSQL)]
```

---

## Phase 2 — Syllabus Refinement

**Framework:** LangGraph
**Pattern:** Parallel Evaluator Nodes + Conditional Routing

### What Happens

Four evaluator nodes run fully in parallel, each evaluating the syllabus on a single independent axis. They each produce a score and specific actionable feedback. The Aggregator collects all four outputs. If all pass, syllabus is approved. If any fail, the aggregated feedback routes back to Phase 1 Expander with precise instructions on what to fix.

### Skills Used
- `academic_level_calibrator.md` — used by Level Evaluator

### MCP Used
- **PostgreSQL MCP** — reads syllabus, writes approved syllabus
- **Reference Database MCP** — Level and Relevance evaluators check against accreditation standards

```mermaid
flowchart TD
    DB[(PostgreSQL)] -->|PostgreSQL MCP| SYL[Syllabus v1]

    subgraph LG["LangGraph — Parallel Evaluators"]
        SYL --> FO[Fan-out]
        FO --> LV["Level Evaluator\nIs depth right for UG/PG/PhD?"]
        FO --> SQ["Sequence Evaluator\nIs topic order pedagogically sound?"]
        FO --> HR["Hours Evaluator\nIs it achievable in semester hours?"]
        FO --> RL["Relevance Evaluator\nIs it industry/research relevant?"]
        LV & SQ & HR & RL --> AG["Aggregator Node\nCollects scores + feedback"]
        AG --> DEC{All Pass?}
        DEC -->|Yes| APP[Approved Syllabus]
        DEC -->|No| FB["Targeted Feedback\nper evaluator"]
    end

    APP -->|PostgreSQL MCP| DB2[(PostgreSQL)]
    FB -->|Routes back with feedback| P1EX[Phase 1\nExpander Node]
```

---

## Phase 3 — Course Outcomes + Bloom's Taxonomy

**Framework:** PhiData (Agno)
**Pattern:** Single ReAct Agent with MD Skill as Tool

### What Happens

A single capable agent with the Bloom's Taxonomy MD skill as a consultable tool. The agent reasons about the full syllabus, consults the taxonomy reference when needed, generates 5-8 Course Outcomes, maps each to the correct Bloom's level with appropriate verbs, writes Sub-COs, then self-checks that all syllabus topics are covered and that Bloom's levels are appropriately distributed. Output is strictly structured JSON.

### Why PhiData Here, Not LangGraph

This is the only phase where the task is **genuinely self-contained single-agent reasoning**. LangGraph would add graph overhead for what is a single agent with a single tool. PhiData's Agent class is purpose-built for this pattern — clean tool use, structured output enforcement, and internal reasoning loop in one definition.

### Skills Used
- `blooms_taxonomy.md` — primary tool the agent consults (via File System MCP at runtime)
- `co_writing_guidelines.md` — verb usage, CO structure, what makes a well-formed CO
- `academic_level_calibrator.md` — ensures COs match course level

### MCP Used
- **File System MCP** — agent reads MD skill files at runtime
- **PostgreSQL MCP** — reads approved syllabus, writes COs + Sub-COs

```mermaid
flowchart TD
    DB[(PostgreSQL\nApproved Syllabus)] -->|PostgreSQL MCP| AGT

    subgraph PD["PhiData ReAct Agent"]
        AGT[Agent Reasoning Loop]
        AGT -->|Needs reference| FS[File System MCP\nRead blooms_taxonomy.md]
        FS -->|Injects into context| AGT
        AGT -->|Needs reference| CW[File System MCP\nRead co_writing_guidelines.md]
        CW -->|Injects into context| AGT
        AGT --> GEN[Generate COs\nwith Bloom levels + verbs]
        GEN --> CHK{Self-check\nCoverage + Distribution OK?}
        CHK -->|No — missing topics or\nBloom levels too low| AGT
        CHK -->|Yes| OUT
    end

    OUT["Structured JSON Output\nCO, Bloom Level, Verbs,\nTopics Covered, Sub-COs"]
    OUT -->|PostgreSQL MCP| DB2[(PostgreSQL)]
```

---

## Phase 4 — Lecture-wise Planning

**Framework:** None (Direct LLM Call)
**Pattern:** Single structured LLM call with JSON output schema

### What Happens

Takes the approved syllabus and COs as input. One LLM call with a strict output schema. Allocates topics into lectures, determines pacing, maps each lecture to the COs it addresses. Nothing is uncertain here — this is allocation logic, not reasoning. Output is the lecture plan array that drives Phases 5a and 5b.

### Output Schema (per lecture)
```json
{
  "lecture_number": 1,
  "title": "Introduction to ...",
  "duration_minutes": 60,
  "subtopics": ["subtopic_1", "subtopic_2"],
  "cos_addressed": ["CO1", "CO3"],
  "bloom_levels_targeted": ["Remember", "Understand"],
  "prerequisite_lectures": []
}
```

### MCP Used
- **PostgreSQL MCP** — reads syllabus + COs, writes lecture plan array

```mermaid
flowchart LR
    DB[(PostgreSQL\nSyllabus + COs)] -->|PostgreSQL MCP| LLM[Single LLM Call\nStrict JSON Schema]
    LLM --> LP[Lecture Plan Array\nN lecture objects]
    LP -->|PostgreSQL MCP| DB2[(PostgreSQL)]
```

---

## Phase 5a — PPT Generation

**Framework:** LangGraph with Send API
**Pattern:** Outline Agent → Dynamic Slide-level Parallel Subagents → Assembly
**Execution:** Sequential per lecture (Lecture 1 complete before Lecture 2 starts)

### What Happens

**Node 1 — Slide Outline Agent:** Reads the full lecture plan. Produces a slide-by-slide outline — title, which subtopic it belongs to, its narrative role (intro / concept / example / summary), and a brief one-line description. This node sees the entire lecture to preserve narrative arc and difficulty progression.

**Node 2 — Send API Fan-out:** Dynamically spawns one subagent per slide based on the outline output. Number of slides is not known until the outline is produced — Send API handles this at runtime.

**Each Slide Agent receives:**
- Its own outline entry
- Summary of the previous slide (for continuity)
- Title of the next slide (for setup)
- Course level (for depth calibration)

**Node 3 — Assembly + Consistency:** Collects all slide outputs. Runs a consistency pass on terminology, difficulty curve, and visual language. Produces final PPT structure passed to Document Generation MCP.

### Why Slide-level, Not Subtopic-level Parallelism

A PPT is a **narrative arc**. Subtopic-level subagents produce coherent islands that stitch together awkwardly. Slide-level parallelism distributes content generation while the outline node preserves the global structure. Context size is not a real constraint at the lecture level — the real constraint is content quality, which is solved by the outline-first approach.

### Skills Used
- `slide_structure.md` — information density, what belongs on slide vs notes, visual hierarchy
- `blooms_taxonomy.md` — slide objectives must map to lecture COs
- `continuity_guidelines.md` — used by assembly node

### MCP Used
- **PostgreSQL MCP** — reads lecture plan
- **Document Generation MCP** — renders final PPTX and saves to MinIO

```mermaid
flowchart TD
    LP[(PostgreSQL\nLecture N Plan)] -->|PostgreSQL MCP| OA

    subgraph LG["LangGraph — Per Lecture"]
        OA["Slide Outline Agent\nFull lecture view\nProduces slide titles +\nnarrative roles + subtopic mapping"]

        OA --> SO[Slide Outline Array]

        SO --> SEND["Send API\nDynamic fan-out\nOne subgraph per slide"]

        subgraph PAR["Parallel Slide Agents"]
            SEND --> S1["Slide 1 Agent\n+ prev slide summary\n+ next slide title"]
            SEND --> S2["Slide 2 Agent\n+ prev slide summary\n+ next slide title"]
            SEND --> S3["Slide 3 Agent\n+ prev slide summary\n+ next slide title"]
            SEND --> SN["Slide N Agent\n+ prev slide summary\n+ next slide title"]
        end

        S1 & S2 & S3 & SN --> AS["Assembly + Consistency Node\nTerminology check\nDifficulty curve check\nFinal PPT structure"]
    end

    AS -->|Document Generation MCP| PPTX[(PPTX\nMinIO)]
```

---

## Phase 5b — Notes Generation

**Framework:** LangGraph with Send API
**Pattern:** Orchestrator → Dynamic Subtopic-level Parallel Subagents → Assembly → QA
**Execution:** After PPT for same lecture is complete. Sequential per lecture.

### What Happens

**Node 1 — Notes Orchestrator:** Reads the full PPT content for the lecture. Divides into subtopic packages — each package contains the slides belonging to that subtopic plus surrounding context.

**Node 2 — Send API Fan-out:** Spawns one notes agent per subtopic. Each agent gets its PPT slides, a summary of what the previous subtopic covered, and the course level. Generates long-form notes: explanation, derivations, worked examples, references, connections to COs.

**Node 3 — Notes Assembler:** Stitches subtopic notes into one document. Adds transitions between subtopics. Enforces consistent terminology across the document.

**Node 4 — QA Gate:** Calls Quality/Plagiarism MCP. If content fails, triggers targeted regeneration of the specific failing subtopic — not a full redo.

### Why Subtopic-level (Not Slide-level) Here

Notes output per subtopic is genuinely large — 2,000–4,000 tokens each. Unlike slides, subtopic notes ARE relatively self-contained because the PPT already provides the structure the agent expands on. Parallel generation here gives real quality AND throughput gains.

### Skills Used
- `blooms_taxonomy.md` — notes depth should reflect CO Bloom levels
- `academic_level_calibrator.md` — explanation depth per UG/PG/PhD
- `continuity_guidelines.md` — transitions between subtopics

### MCP Used
- **PostgreSQL MCP** — reads lecture plan + PPT content reference
- **Quality/Plagiarism MCP** — QA gate check
- **Document Generation MCP** — renders final notes MD/PDF, saves to MinIO

```mermaid
flowchart TD
    PPTX[(PPT Content\nfrom Phase 5a)] --> NO
    LP[(PostgreSQL\nLecture Plan)] -->|PostgreSQL MCP| NO

    subgraph LG["LangGraph — Per Lecture"]
        NO["Notes Orchestrator\nReads full PPT content\nDivides into subtopic packages"]

        NO --> SEND["Send API\nDynamic fan-out\nOne subgraph per subtopic"]

        subgraph PAR["Parallel Subtopic Agents"]
            SEND --> ST1["Subtopic 1 Agent\nPPT slides for this subtopic\n+ prev subtopic summary\n+ course level"]
            SEND --> ST2["Subtopic 2 Agent\nPPT slides for this subtopic\n+ prev subtopic summary\n+ course level"]
            SEND --> ST3["Subtopic 3 Agent\nPPT slides for this subtopic\n+ prev subtopic summary\n+ course level"]
            SEND --> STN["Subtopic N Agent\nPPT slides for this subtopic\n+ prev subtopic summary\n+ course level"]
        end

        ST1 & ST2 & ST3 & STN --> NA["Notes Assembler\nStitch subtopics\nAdd transitions\nTerminology pass"]

        NA --> QAG{QA Gate\nQuality + Plagiarism MCP}
        QAG -->|Pass| OUT[Final Notes]
        QAG -->|Fail — specific subtopic| TR["Targeted Regeneration\nFailing subtopic only"]
        TR --> NA
    end

    OUT -->|Document Generation MCP| NT[(Notes MD / PDF\nMinIO)]
```

---

## MCP Layer

MCP (Model Context Protocol) provides a **standardized interface** between agents and external systems. Agents call MCP servers using a consistent protocol — swapping the underlying system (e.g. changing storage from MinIO to S3) requires no changes to agent code.

```mermaid
flowchart LR
    subgraph AGENTS["Agent Pipeline"]
        P1[Phase 1\nLangGraph]
        P2[Phase 2\nLangGraph]
        P3[Phase 3\nPhiData]
        P4[Phase 4\nDirect LLM]
        P5A[Phase 5a\nLangGraph]
        P5B[Phase 5b\nLangGraph]
    end

    subgraph MCP["MCP Servers"]
        FS["File System MCP\nRead curriculum\nRead MD Skill files"]
        PG["PostgreSQL MCP\nRead/write syllabus\nCOs, lecture plans"]
        DG["Document Generation MCP\nRender PPTX\nRender Notes MD/PDF"]
        RD["Reference Database MCP\nAccreditation standards\nStandard curricula"]
        QC["Quality/Plagiarism MCP\nContent quality check\nOriginality check"]
    end

    subgraph STORAGE["Storage"]
        MN[(MinIO\nCurriculum files\nPPTX, Notes)]
        DB[(PostgreSQL\nSyllabus, COs\nLecture Plans)]
        RDB[(Reference DB\nStandards, Templates)]
    end

    P1 & P3 --> FS
    P1 & P2 & P3 & P4 & P5A & P5B --> PG
    P5A & P5B --> DG
    P2 & P3 --> RD
    P5B --> QC

    FS --> MN
    PG --> DB
    DG --> MN
    RD --> RDB
```

### MCP Server Responsibilities

| MCP Server | Phases | What It Does |
|---|---|---|
| **File System MCP** | 1, 3 | Reads curriculum files from MinIO. Reads MD Skill files at agent runtime |
| **PostgreSQL MCP** | 1, 2, 3, 4, 5a, 5b | Central state store. Each phase reads previous phase output and writes its own |
| **Document Generation MCP** | 5a, 5b | Agents pass structured content — MCP handles rendering PPTX and MD/PDF files |
| **Reference Database MCP** | 2, 3 | Evaluators check against accreditation standards. Phase 3 checks standard CO patterns |
| **Quality/Plagiarism MCP** | 5b | QA gate at notes generation. Returns score + specific failing sections |

---

## Skills Layer

Skills are **reusable capabilities** injected into agent context at runtime. Two types: knowledge skills (MD files read via File System MCP) and computational skills (Python modules executed directly).

```mermaid
flowchart TD
    subgraph MD["Knowledge Skills — MD Files\n(Read via File System MCP at runtime)"]
        BT["blooms_taxonomy.md\nVerb lists per level\nDistribution guidelines\nSelf-check rules\nExamples of good/bad COs"]
        SS["slide_structure.md\nInformation density rules\nSlide vs notes split\nVisual hierarchy\nPedagogical guidelines"]
        AL["academic_level_calibrator.md\nUG / PG / PhD depth benchmarks\nVocabulary expectations\nComplexity indicators"]
        CC["continuity_guidelines.md\nFlow between slides\nTransitions between subtopics\nPrerequisite signposting"]
        CW["co_writing_guidelines.md\nCO structure templates\nVerb usage by level\nCoverage check rules"]
    end

    subgraph PY["Computational Skills — Python Modules\n(Executed directly, not injected into context)"]
        CP["curriculum_parser.py\nParse MD/PDF curricula\nHandle format variations\nExtract structured topics"]
        PC["plagiarism_checker.py\nCall external check API\nReturn score + flagged sections"]
        PR["pptx_renderer.py\nStructured JSON → PPTX file\nApply slide templates"]
        NF["notes_formatter.py\nMD content → formatted PDF\nApply notes templates"]
    end

    subgraph USAGE["Which Phase Uses Which Skill"]
        U1["Phase 1\ncurriculum_parser.py\nacademic_level_calibrator.md"]
        U2["Phase 2\nacademic_level_calibrator.md"]
        U3["Phase 3\nblooms_taxonomy.md\nco_writing_guidelines.md\nacademic_level_calibrator.md"]
        U4["Phase 4\n(no skills needed)"]
        U5A["Phase 5a\nslide_structure.md\nblooms_taxonomy.md\ncontinuity_guidelines.md\npptx_renderer.py"]
        U5B["Phase 5b\nblooms_taxonomy.md\nacademic_level_calibrator.md\ncontinuity_guidelines.md\nplagiarism_checker.py\nnotes_formatter.py"]
    end
```

### Why MD Files for Knowledge Skills

MD skills work exactly like Claude's own skill system — the agent reads the file via File System MCP, the content is injected into its context before reasoning begins, and the agent applies that knowledge during generation. Benefits:

- Domain experts (faculty) can author and refine skills directly — no engineering needed
- Skill updates take effect immediately without redeployment
- Human-readable and version-controllable in Git
- Multiple agents across multiple phases share the same skill definition

---

## Full Framework Decision Summary

| Phase | Framework | Pattern | Key Reason |
|---|---|---|---|
| **Phase 1** Syllabus Expansion | LangGraph | Generator-Critic Cycle | Conditional cyclic routing is LangGraph's core strength |
| **Phase 2** Syllabus Refinement | LangGraph | Parallel Evaluators + Conditional Routing | Independent evaluation axes with fan-out/fan-in and cross-phase routing on failure |
| **Phase 3** Bloom's Taxonomy + COs | PhiData (Agno) | Single ReAct Agent + MD Tool | Self-contained single agent with tool — PhiData's exact design target. No graph overhead needed |
| **Phase 4** Lecture Planning | None | Direct LLM Call | Zero uncertainty, zero loops — a framework would just be overhead on a function call |
| **Phase 5a** PPT Generation | LangGraph | Outline → Send API → Assembly | Dynamic N-slide parallelism unknown until runtime — Send API handles this natively |
| **Phase 5b** Notes Generation | LangGraph | Orchestrator → Send API → Assembly → QA | Dynamic M-subtopic parallelism + QA gate with targeted regeneration |

---

## Curriculum Storage Decision

| Asset | Storage | Format | Reason |
|---|---|---|---|
| Curriculum | MinIO | **MD (preferred)** or PDF | Read once, fully, at Phase 1. No retrieval needed. MD gives clean structure |
| Syllabus | PostgreSQL | JSONB | Queried and updated across Phases 1 and 2 |
| Course Outcomes | PostgreSQL | JSONB | Referenced by Phases 4, 5a, 5b |
| Lecture Plan | PostgreSQL | JSONB | Drives Phases 5a and 5b |
| PPT Files | MinIO | PPTX | File artifact, served to user |
| Notes Files | MinIO | MD / PDF | File artifact, served to user |
| Cross-curriculum index | Qdrant | Embeddings | **Only if** cross-curriculum search is built — not needed for the core pipeline |

> **Note on Embeddings:** The curriculum is read **once, fully** at Phase 1. Chunking it into embeddings would hurt comprehension by breaking document-level structure. Add embeddings only if you build cross-curriculum search or discovery features as a separate use case.

---

## Skills Directory Structure

```
/skills
  /knowledge                        ← MD files — authored by domain experts
    blooms_taxonomy.md
    slide_structure.md
    academic_level_calibrator.md
    continuity_guidelines.md
    co_writing_guidelines.md

  /computational                    ← Python modules — authored by engineers
    curriculum_parser.py
    plagiarism_checker.py
    pptx_renderer.py
    notes_formatter.py
```
