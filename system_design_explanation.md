# Educational Content Generation Pipeline
## Complete System Design — What We Are Building and How Everything Interacts

---

## Document Purpose

This document explains the complete agentic pipeline for generating educational content across 200+ courses. It covers what each component is, what it does, why it exists, and how every piece interacts with every other piece. This is not a code guide — it is a system understanding document. Every person working on any part of this system should read this document in full before writing a single line of code or a single prompt.

---

## What We Are Building — The Big Picture

We are building a pipeline that takes a raw course curriculum document as input and produces, without human intervention, a fully structured syllabus, a set of course outcomes mapped to Bloom's taxonomy, a lecture-by-lecture content plan, presentation slides for every lecture, and detailed lecture notes for every lecture.

This pipeline must work for more than 200 different courses spanning different domains, different academic levels, and different credit structures. It runs on two DGX clusters with 16 H100 GPUs and is designed for quality, consistency, and scale simultaneously.

The pipeline is not a chatbot. It is not a single LLM call. It is a structured, multi-phase agentic system where each phase has a specific job, specific tools, and specific quality criteria. Phases pass structured data to each other. No phase starts until the previous phase has produced validated output.

---

## System-Wide Architecture

The system is divided into six phases. Phases 1 through 4 are strictly sequential. Phase 5a and 5b are also sequential with respect to each other but operate in parallel at the lecture level.

```
Curriculum Input (MD or PDF file)
          │
          ▼
    ┌─────────────────────────────────┐
    │  Phase 1: Syllabus Expansion    │
    │  Framework: LangGraph           │
    └─────────────────────────────────┘
          │ Validated structured syllabus
          ▼
    ┌─────────────────────────────────┐
    │  Phase 2: Syllabus Refinement   │
    │  Framework: LangGraph           │
    └─────────────────────────────────┘
          │ Refined and approved syllabus
          ▼
    ┌─────────────────────────────────┐
    │  Phase 3: Course Outcomes +     │
    │  Bloom's Taxonomy Mapping       │
    │  Framework: PhiData (Agno)      │
    └─────────────────────────────────┘
          │ Structured COs and Sub-COs
          ▼
    ┌─────────────────────────────────┐
    │  Phase 4: Lecture-wise Planning │
    │  Framework: None (direct call)  │
    └─────────────────────────────────┘
          │ Lecture plan array
          ▼
    ┌─────────────────────────────────┐
    │  Phase 5a: PPT Generation       │
    │  Framework: LangGraph           │
    └─────────────────────────────────┘
          │ PPT content per lecture
          ▼
    ┌─────────────────────────────────┐
    │  Phase 5b: Notes Generation     │
    │  Framework: LangGraph           │
    └─────────────────────────────────┘
          │
          ▼
    Final Output: PPTX files + Notes files
    Stored in MinIO/S3
```

---

## The Three-Layer System: Skills, Tools, MCP

Before going into phases, it is essential to understand the three supporting layers that all phases depend on. These are not the same thing. They serve fundamentally different purposes and must not be confused with each other.

---

### Layer 1: Skills (Knowledge Injected Into Agents)

Skills are markdown files that contain domain knowledge. They exist because LLM agents reason better when they are given structured, specific knowledge in their context rather than relying on general training knowledge alone.

A skill is not a tool the agent calls. A skill is knowledge the agent reads before it starts thinking. Think of it like giving a subject matter expert a reference manual to read before they begin their work. The agent internalizes the skill content and applies it during reasoning.

Skills are stored as MD files in a central skills repository. Every time an agent starts, the relevant skill files are loaded and injected into the agent's context via the File System MCP server. This means skills can be updated, refined, and improved by domain experts at any time without changing any code. If the Bloom's taxonomy mapping skill needs a correction, a faculty member edits the MD file — no engineering involvement required.

Skills are always-used. There is no decision involved in whether to apply a skill. If a skill is assigned to a phase, it is always loaded and always injected.

---

### Layer 2: Tools (Capabilities Agents Decide to Use)

Tools are capabilities that agents can choose to invoke during their reasoning process. The key distinction from skills is the decision element. An agent reads skills passively before reasoning. An agent actively decides whether to call a tool, when to call it, and what to pass to it, based on what it encounters during reasoning.

Tools are exposed as callable endpoints via MCP servers. The agent sees a list of available tools and their descriptions, and during its reasoning loop it can say "I need to check something — I will call this tool now." The tool runs, returns a result, and the agent continues reasoning with that new information.

The agent may or may not use a given tool in any given run. If the curriculum is from a standalone course with no prerequisite overlaps, the similarity search tool may never be needed. If the curriculum is from an advanced course building on multiple prerequisites, the agent may call the similarity search tool multiple times.

---

### Layer 3: MCP Servers (External System Connections)

MCP (Model Context Protocol) servers are the standardized way that agents connect to external systems. Every external system the pipeline needs to interact with — file storage, the database, document renderers, reference databases — is accessed through an MCP server.

MCP is not a framework for agent reasoning. It is a protocol for connecting agents to capabilities outside themselves. It exists so that the internal agent code never has to know how a specific system works. The agent calls a standard MCP interface, and the MCP server handles the specifics of connecting to PostgreSQL, or MinIO, or Qdrant, or whatever the target system is.

This means that if the storage backend changes from MinIO to S3, only the MCP server implementation changes. Not a single agent node or graph changes. This is the architectural benefit of MCP — decoupling agent logic from infrastructure.

---

## Skills Reference — Complete Descriptions

### Skill: Academic Level Calibrator

**File:** `academic_level_calibrator.md`

**Purpose:** This skill teaches agents how to calibrate the depth, complexity, vocabulary, and scope of content for different academic levels. The three levels it covers are Undergraduate (UG), Postgraduate (PG), and PhD. Without this skill, an LLM will produce content that is generically academic — it will not know whether to explain a concept from scratch or assume prior graduate-level knowledge. With this skill, the agent knows exactly what prior knowledge to assume, what depth to go to, how many hours a subtopic should take, and what vocabulary level is appropriate.

**What the skill contains:** The skill contains a detailed definition of each academic level with concrete examples of what appropriate depth looks like. It contains guidelines for estimated hours per subtopic at each level. It contains vocabulary expectations — what terms can be assumed known, what terms must be defined. It contains a calibration checklist that the agent must mentally run through before finalizing any content, asking questions like "Is this depth appropriate for the stated level?" and "Am I assuming knowledge the student at this level would not have?"

**Which phases use it:** Phase 1 uses it when deciding how deeply to expand subtopics. Phase 2 uses it in the Level Evaluator node to check if the expansion is appropriately calibrated. Phase 3 uses it to ensure Course Outcomes are written at the right cognitive challenge for the level. Phases 5b uses it to control the depth and complexity of lecture notes explanations.

**Who maintains it:** This skill should be maintained jointly by academic staff and the engineering team. Academic staff define what appropriate depth means at each level. Engineering ensures the formatting stays consistent.

---

### Skill: Bloom's Taxonomy Reference

**File:** `blooms_taxonomy.md`

**Purpose:** This skill is the authoritative reference for Bloom's Taxonomy of Educational Objectives. It exists because LLMs, without specific guidance, misuse Bloom's taxonomy consistently. They cluster Course Outcomes at lower cognitive levels (Remember, Understand) and avoid higher-order thinking levels (Analyze, Evaluate, Create). They use verbs inconsistently — writing "understand" as a CO verb when "understand" is not a measurable, assessable action. This skill corrects all of that by giving the agent the exact verb lists, level definitions, and distribution rules it needs.

**What the skill contains:** The skill contains all six Bloom's levels with their definitions: Remember, Understand, Apply, Analyze, Evaluate, Create. For each level it contains an extensive list of approved action verbs. It contains rules for verb selection — which verbs are measurable and which are not (for example "know" and "understand" are not usable as CO verbs because they cannot be directly assessed). It contains distribution guidelines — for a UG course, what mix of Bloom's levels is appropriate across the set of COs. It contains examples of poorly written COs and their corrected versions. It contains a self-check checklist for the agent to run before finalizing: "Does every CO use an approved action verb? Does the full set of COs span an appropriate range of Bloom's levels? Does every CO map to at least one subtopic in the syllabus?"

**Which phases use it:** Phase 3 is the primary user — the entire CO generation task is driven by this skill. Phase 5a uses it in the slide outline agent to ensure slide learning objectives align with the COs the lecture is responsible for. Phase 5b uses it to calibrate the depth of explanations in notes — a CO at the Analyze level should be accompanied by notes that actually develop analytical reasoning, not just descriptive content.

**Who maintains it:** This is a domain-stable skill. Bloom's taxonomy does not change. However, the distribution guidelines and examples should be reviewed by academic staff familiar with the institution's accreditation requirements, as those requirements may impose specific CO coverage expectations.

---

### Skill: Slide Structure Guidelines

**File:** `slide_structure.md`

**Purpose:** This skill defines what makes a good lecture slide. It exists because LLMs without guidance produce slides that are either too text-heavy (paragraphs of content on each slide) or too sparse (meaningless bullet points). Neither serves the pedagogical purpose of a lecture slide. This skill teaches the agent the craft principles of effective slide design for academic lectures.

**What the skill contains:** The skill contains rules for information density — how many key points should appear on a single slide, and what the maximum word count for any single slide should be. It contains the distinction between what belongs on the slide (the core idea, key terms, a diagram reference, a formula) versus what belongs in the speaker notes (the explanation, the example, the elaboration). It contains guidelines for narrative role — the concept that each slide has a role in the lecture story: introduction, concept definition, worked example, comparison, summary, transition. It contains guidelines for difficulty escalation — how the cognitive demand of slides should increase as the lecture progresses. It contains specific guidance on when to use a diagram reference versus text, and what kind of visual suggestion to include in the slide output. It contains guidance on connecting each slide to the learning objectives of the lecture, so every slide earns its place.

**Which phases use it:** Phase 5a exclusively. The slide outline agent uses it to plan the role of each slide before content is generated. Each slide content subagent uses it to ensure the content it generates for its assigned slide matches the slide's role and density rules.

**Who maintains it:** This skill benefits from input from faculty who teach regularly and know from experience what slide approaches work in the classroom. It should be treated as a living document that improves over time as the system generates more content and quality patterns emerge.

---

### Skill: Continuity Guidelines

**File:** `continuity_guidelines.md`

**Purpose:** This skill defines what good continuity looks like within a lecture and across a course. It exists to prevent a common failure mode in LLM-generated educational content — each unit or slide is locally coherent but there is no thread connecting them. A student reading the generated content should feel like it flows naturally, with each idea building on the previous. Without this skill, parallel agents generating slides or subtopic notes have no awareness of what came before or after, and the assembled output feels disjointed.

**What the skill contains:** The skill contains rules for slide-level continuity — how the closing of one slide should relate to the opening of the next. It contains rules for subtopic-level continuity in notes — how a new subtopic's notes should acknowledge what the previous subtopic established before introducing new concepts. It contains rules for terminology consistency — if a term was defined one way earlier in the lecture, it must be used consistently throughout. It contains rules for example continuity — if an illustrative example was introduced early in a lecture, it should be carried through later slides rather than introducing a completely new example. It contains a checklist for the assembly nodes in phases 5a and 5b to verify continuity before finalizing the output.

**Which phases use it:** Phase 5a uses it in the assembly and consistency check node after all slide agents have produced their content. Phase 5b uses it in the notes assembler node after all subtopic agents have produced their content. It is never used in Phases 1 through 4 because those phases work at the course and unit level where continuity considerations are different.

**Who maintains it:** Engineering team with input from faculty. The rules in this skill are derived from instructional design principles. They should be stable once well-written.

---

### Skill: Course Outcome Writing Guidelines

**File:** `co_writing_guidelines.md`

**Purpose:** This skill teaches the agent how to write well-formed Course Outcomes. It complements the Bloom's Taxonomy skill, which tells the agent what levels and verbs to use. This skill tells the agent how to construct the sentences, how many COs to write, how to ensure measurability, and how to ensure full syllabus coverage.

**What the skill contains:** The skill contains the standard CO sentence structure: "Upon completion of this course, students will be able to [Bloom's verb] [specific knowledge/skill] [context or condition where applicable]." It contains rules for specificity — COs must be specific enough to be assessable, not vague statements of intent. It contains rules for coverage — the full set of COs must collectively cover all major units of the syllabus; no major unit should be orphaned without a CO. It contains rules for count — typically 5 to 8 COs per course, not more. It contains the relationship between COs and Sub-COs — Sub-COs break a CO down into the specific, measurable components that can be tied to individual lectures. It contains institutional accreditation requirements relevant to CO writing if applicable.

**Which phases use it:** Phase 3 exclusively. This skill is the primary craft guide for the CO generation agent.

**Who maintains it:** Academic staff with knowledge of the institution's accreditation requirements. This skill is the most institutionally specific of all skills and must be kept aligned with NBA, NAAC, or other relevant accreditation body requirements as they evolve.

---

### Skill: Curriculum Parser Instructions

**File:** `curriculum_parser_instructions.md`

**Purpose:** This skill guides the metadata extraction step at the start of Phase 1. Raw curriculum documents come in many formats — some are well-structured with clear unit headings, some are dense paragraphs, some use inconsistent numbering, some have abbreviations. This skill teaches the LLM how to handle each of these cases and extract consistent structured information regardless of input format.

**What the skill contains:** Rules for extracting course name, code, level, credit hours, and prerequisites from different document layouts. Rules for grouping flat topic lists into logical units when no unit structure is provided. Rules for inferring course level from course code when not explicitly stated. Rules for handling abbreviations — when to expand them and when to leave them. Rules for handling duplicate or overlapping topics in the raw curriculum. Rules for flagging vague entries like "Advanced Topics" that need special treatment in the expander.

**Which phases use it:** Phase 1 only, specifically in the curriculum loader step before the expansion begins.

**Who maintains it:** Engineering team. This is a technical skill about document parsing, not academic content.

---

## MCP Servers Reference — Complete Descriptions

### MCP Server: File System MCP

**What it connects to:** MinIO object storage (S3-compatible), which stores all raw files and generated output files.

**What it exposes to agents:**

The File System MCP exposes three categories of operations. First, reading curriculum files — agents in Phase 1 call this to retrieve the raw curriculum MD or PDF for the course being processed. Second, reading skill files — this is how all agents load their skill MD files. Every skill injection goes through the File System MCP, which reads from the skills repository in MinIO. Third, writing generated output files — Phase 5a writes completed PPTX files here, Phase 5b writes completed notes MD or PDF files here.

**Why MCP and not direct file access:** Two reasons. First, decoupling — if the storage backend changes from MinIO to a different system, only this MCP server changes. No agent code changes. Second, skill file serving — because skills are loaded at runtime via this server, skills can be updated in MinIO and the next agent run will pick up the new version without any deployment.

**Which phases use it:** All phases for skill loading. Phase 1 for curriculum reading. Phases 5a and 5b for writing generated output.

---

### MCP Server: PostgreSQL MCP

**What it connects to:** A PostgreSQL database that serves as the structured state store for the entire pipeline.

**What it exposes to agents:**

The PostgreSQL MCP exposes read and write operations for the structured outputs of each phase. Phase 1 writes the expanded syllabus here as JSONB. Phase 2 reads the Phase 1 syllabus and writes the refined syllabus. Phase 3 reads the refined syllabus and writes the COs and Sub-COs. Phase 4 reads the syllabus and COs and writes the lecture plan array. Phase 5a reads the lecture plan and writes the PPT content structure. Phase 5b reads the lecture plan and the PPT content.

The MCP server also exposes a check operation — before processing a course, the pipeline checks if a syllabus already exists for that course code to avoid reprocessing.

**Why MCP and not direct DB access:** The MCP server enforces the read/write interface contract. Agents only see the operations they are supposed to perform. No agent has raw SQL access. This prevents agents from reading data they should not have access to and prevents accidental writes to the wrong tables.

**Database schema overview:**

The database has one table per phase output. The syllabus table stores the complete SyllabusDraft JSON alongside course code, phase status, and iteration metadata. The outcomes table stores COs and Sub-COs with Bloom's level mapping. The lecture plan table stores the lecture-by-lecture breakdown. The PPT content table stores the structured slide data per lecture. All tables are keyed by course code and include timestamps and processing metadata for observability.

**Which phases use it:** All phases read from it (for previous phase outputs) and write to it (for their own outputs).

---

### MCP Server: Reference Database MCP

**What it connects to:** An internal database of academic reference materials — accreditation standards, benchmark curricula from reputable institutions, learning outcome frameworks such as NBA and NAAC guidelines, and domain-specific curriculum standards.

**What it exposes to agents:**

The Reference Database MCP exposes lookup operations. Phase 2's Relevance Evaluator can query it to check whether the syllabus content aligns with current industry and academic standards for the domain. Phase 3's CO generation agent can query it to verify that COs are being written in alignment with the accreditation framework the institution follows.

**Why this is an MCP tool and not a skill:** This is a live database of reference material that grows and changes. It is too large to inject into context as a skill file. The agent queries it selectively — only for the specific domain and level it needs — rather than having the entire database in context.

**Which phases use it:** Phase 2 (Relevance Evaluator node) and Phase 3 (CO generation agent).

---

### MCP Server: Document Generation MCP

**What it connects to:** The document rendering services that produce actual files from structured content data. One renderer handles PPTX generation from structured slide JSON. Another handles PDF and MD notes generation from structured notes content.

**What it exposes to agents:**

The Document Generation MCP exposes two operations. The PPTX renderer takes the structured slide data produced by Phase 5a (slide titles, content blocks, speaker notes, visual suggestions) and produces an actual PPTX file, which is then stored via the File System MCP. The notes renderer takes the assembled notes content from Phase 5b and produces a formatted MD file and a rendered PDF, both stored via the File System MCP.

**Why the agents do not generate the files themselves:** Agents produce structured content — JSON describing what should be on each slide, text content for each subtopic's notes. The actual file formatting and rendering is deterministic work that should not be inside an LLM's reasoning loop. Separating content generation (agent) from file rendering (MCP server) means the rendered format can change without touching any agent. If the institution wants to change the slide template, only the PPTX renderer changes.

**Which phases use it:** Phase 5a for PPTX files. Phase 5b for notes files.

---

### MCP Server: Qdrant MCP

**What it connects to:** A Qdrant vector database that stores embeddings of topics from all 200+ course curricula.

**What it exposes to agents:**

The Qdrant MCP exposes a similarity search operation. Given a list of topic names, it returns the most similar topics found in other courses, along with which course they belong to, the course code, and the coverage level (introductory, intermediate, advanced).

**Why this is a tool and not a skill:** This is a retrieval operation against a live database. The results change as more curricula are processed. It cannot be a static skill file.

**When agents use it:** In Phase 1, the Expander agent may use this to check whether a topic it is about to expand is already covered in a prerequisite course. For example, if a course on Machine Learning lists "Linear Algebra" as a prerequisite, and the Qdrant search reveals that Linear Algebra is covered in depth in the prerequisite Mathematics course, the Expander knows not to re-expand it as a primary subtopic. This prevents curriculum duplication and respects prerequisite structures.

**Which phases use it:** Phase 1 (Expander node, as a tool the agent decides to call).

---

### MCP Server: Custom Tools MCP

**What it connects to:** A collection of small, specialized utilities that do not fit any of the above servers.

**What it exposes:**

The Credit Hour Calculator takes a list of subtopics with estimated hours and returns whether the total is within an acceptable range of the stated credit hours. This is simple arithmetic, but exposing it as an MCP tool means the agent gets a deterministic, reliable result rather than relying on LLM arithmetic which can be unreliable.

The Image and Diagram Search takes a concept or topic name and returns references to relevant diagrams, charts, or visual references. Phase 5a's slide agents use this when they determine a concept would benefit from a visual.

The Plagiarism and Originality Checker takes a block of generated text and returns an originality score. Phase 5b's QA gate uses this to verify generated notes are not reproducing source material verbatim.

**Which phases use it:** Phase 2 (Credit Hour Calculator in Hours Evaluator node), Phase 5a (Image/Diagram Search in slide content agents), Phase 5b (Plagiarism Checker in QA gate).

---

## Phase-by-Phase Detailed Explanation

---

### Phase 1: Curriculum to Syllabus Expansion

**Framework:** LangGraph
**Pattern:** Generator-Critic cycle with conditional routing

**What this phase does:**

Phase 1 takes a raw curriculum document and transforms it into a detailed, structured syllabus. A raw curriculum is typically a list of unit names and broad topic headings — it tells you what the course covers but not how deeply, in what sequence at the subtopic level, with what prerequisites, or with what learning intent. Phase 1's job is to expand this sparse outline into a rich syllabus that downstream phases can actually work with.

**Why this is harder than a single LLM call:**

A single LLM call to expand a curriculum will produce something that looks complete but often has hidden problems — topics that assume knowledge not covered in the course, topics in a sequence that makes it harder to learn, depth that does not match the academic level, or coverage gaps where implied topics are missing. These problems are hard to detect from within the same reasoning process that produced the expansion. A critic that evaluates the expansion with fresh eyes, specifically looking for these failure modes, catches problems the expander cannot see in itself.

**The Generator-Critic cycle:**

The Expander node takes the curriculum, the course metadata, the Academic Level Calibrator skill, and the Curriculum Parser Instructions skill, and produces a structured syllabus. The Gap Critic node then takes that syllabus and evaluates it specifically for four types of problems: missing prerequisites (knowledge assumed but not covered), coverage gaps (topics implied but absent), sequencing issues (illogical ordering), and depth mismatches (content not calibrated to course level). If the critic finds problems, it produces specific, actionable feedback and routes back to the Expander. The Expander receives the feedback alongside the original curriculum and produces a revised expansion addressing the specific gaps. This cycle repeats up to three times. After three iterations, the pipeline force-passes regardless, because infinite loops are never acceptable in a production system.

**What the Expander produces:**

A structured object containing course metadata (name, code, level, credit hours, domain, prerequisites), a list of units with unit names, learning intent statements, and total hour allocations, and within each unit a list of subtopics with names, depth levels, estimated hours, descriptions, and any intra-course prerequisites (subtopics within this same course that must come before this subtopic).

**What the Gap Critic evaluates:**

The critic does not rewrite. It only identifies problems. For each problem it finds, it specifies the gap type, the exact location (which unit, which subtopic), a description of what is wrong, and a specific instruction for what the Expander should do to fix it. The critic also reports a confidence score — how certain it is that the gaps it found are real. This confidence score is recorded for observability.

**What Phase 1 passes to Phase 2:**

The final syllabus object, the iteration count used, the phase status (passed cleanly or force-passed), and the last critic feedback for audit purposes.

**Skills used in Phase 1:**
- Academic Level Calibrator (Expander node and Critic node)
- Curriculum Parser Instructions (curriculum loading step)

**Tools available in Phase 1:**
- Similarity Search via Qdrant MCP (Expander node, decides whether to call it)

**MCP servers used in Phase 1:**
- File System MCP — reads curriculum file and skill files
- PostgreSQL MCP — writes final syllabus
- Qdrant MCP — similarity search if invoked

---

### Phase 2: Syllabus Refinement

**Framework:** LangGraph
**Pattern:** Parallel evaluator nodes with fan-out/fan-in and conditional routing

**What this phase does:**

Phase 2 takes the expanded syllabus from Phase 1 and evaluates it against four independent quality dimensions simultaneously. Phase 1 focused on content correctness — is everything there that should be there. Phase 2 focuses on quality fitness — is what is there appropriate, achievable, and aligned.

**Why four parallel evaluators instead of one combined evaluator:**

The four quality dimensions are genuinely independent. Whether the course is at the right academic level has nothing to do with whether it fits within the credit hours. Whether the topic sequencing is pedagogically sound has nothing to do with whether the content is industry-relevant. If one evaluator assessed all dimensions, it would either produce a superficial evaluation across all dimensions or an extremely long reasoning process where one dimension's evaluation influences another. Four independent evaluators each do one thing well, with focused reasoning on their specific dimension.

**The four evaluator nodes:**

The Level Evaluator checks whether the depth and complexity of the syllabus content is appropriate for the stated course level. It uses the Academic Level Calibrator skill and looks specifically at subtopic descriptions, depth level labels, and estimated hours against the level guidelines.

The Sequence Evaluator checks whether the ordering of units and subtopics makes pedagogical sense. It looks for cases where a later unit requires knowledge introduced even later, where foundational concepts appear after advanced applications, or where the difficulty curve has illogical jumps or drops.

The Hours Evaluator checks whether the total estimated hours across all subtopics are within an acceptable range of the credit hours stated in the course metadata. It uses the Credit Hour Calculator tool from the Custom Tools MCP to do this arithmetic deterministically. It also checks whether the hour distribution across units makes sense — no single unit should consume a disproportionate fraction of the total time unless there is a clear reason.

The Relevance Evaluator checks whether the content is current and appropriate for the domain. It queries the Reference Database MCP to compare the syllabus against benchmark curricula and accreditation standards for this domain and level. It looks for topics that are outdated, topics that are conspicuously absent compared to industry standards, and content that does not align with where the field currently stands.

**The aggregator node:**

After all four evaluator nodes complete, the aggregator receives all four evaluation outputs. Each evaluation includes a pass/fail decision and specific feedback. The aggregator makes the final routing decision: if all four evaluators pass, the syllabus proceeds to Phase 3. If any evaluator fails, the aggregator compiles the specific feedback from the failing evaluators and routes the syllabus back to Phase 1's Expander node with that compiled feedback. The syllabus is not re-evaluated by Phase 1's critic — it goes directly to the Expander with targeted instructions for what to fix.

**What Phase 2 passes to Phase 3:**

The refined and approved syllabus, the evaluation results from all four evaluators (stored for audit purposes), and the phase status.

**Skills used in Phase 2:**
- Academic Level Calibrator (Level Evaluator node)

**Tools available in Phase 2:**
- Credit Hour Calculator via Custom Tools MCP (Hours Evaluator node)
- Reference Database Lookup via Reference Database MCP (Relevance Evaluator node)

**MCP servers used in Phase 2:**
- File System MCP — reads skill files
- PostgreSQL MCP — reads Phase 1 syllabus, writes refined syllabus
- Reference Database MCP — accreditation standards lookup
- Custom Tools MCP — credit hour calculation

---

### Phase 3: Course Outcomes and Bloom's Taxonomy Mapping

**Framework:** PhiData (Agno)
**Pattern:** Single ReAct agent with knowledge tools

**What this phase does:**

Phase 3 takes the refined syllabus and produces the Course Outcomes (COs) and Sub-Course Outcomes (Sub-COs) for the course, each correctly mapped to the appropriate Bloom's Taxonomy level with appropriate action verbs.

**Why PhiData instead of LangGraph:**

This phase has one agent doing one self-contained reasoning task. There is no workflow to orchestrate, no conditional routing, no parallel branches. The task involves genuine reasoning complexity — the agent needs to think carefully about what the course is trying to achieve, map those achievements to the right cognitive levels in Bloom's taxonomy, write measurable outcomes with appropriate verbs, and then verify that the full set of outcomes covers the syllabus. PhiData's Agent class is designed exactly for this: a single capable agent with access to tools and knowledge, with built-in support for structured output. Wrapping this in a LangGraph node and graph would add workflow complexity for no benefit.

**What the agent reasons through:**

The agent reads the full refined syllabus and internalizes the academic level and domain context. It reads the Bloom's Taxonomy Reference skill, which gives it the verb lists, level definitions, and distribution guidelines. It reads the Course Outcome Writing Guidelines skill, which gives it the sentence structure and coverage requirements. It then begins reasoning: what should a student be able to do after completing this course? At what cognitive level? How many outcomes are needed? Does the set of outcomes cover all major units?

The agent may use the Reference Database MCP tool if it wants to verify that its proposed outcomes align with accreditation frameworks. This is not automatic — the agent decides whether this lookup is needed based on the course domain and level.

After drafting the COs, the agent performs a self-check: Does every CO use an approved Bloom's action verb? Is the Bloom's level distribution appropriate for this course level? Does every major unit have at least one CO addressing it? Are all COs specific and measurable?

After COs are approved, the agent generates Sub-COs for each CO. Sub-COs are the granular, lecture-level breakdown of what each CO requires. They are the bridge between the CO and the lecture plan.

**What Phase 3 produces:**

A structured list of COs, each with the CO statement, the Bloom's level, the action verb used, the list of syllabus subtopics the CO covers, and a list of Sub-COs. Each Sub-CO has its own statement, Bloom's level, and connection to specific subtopics. This entire structure is written to PostgreSQL via the MCP server.

**Skills used in Phase 3:**
- Bloom's Taxonomy Reference (primary, injected before all reasoning)
- Course Outcome Writing Guidelines (primary, injected before all reasoning)
- Academic Level Calibrator (ensures CO complexity matches course level)

**Tools available in Phase 3:**
- Reference Database Lookup via Reference Database MCP (agent decides whether to call it)
- Web Search (agent decides whether to call it, for verifying current accreditation requirements)

**MCP servers used in Phase 3:**
- File System MCP — reads skill files
- PostgreSQL MCP — reads refined syllabus, writes COs and Sub-COs
- Reference Database MCP — accreditation standards (if tool is invoked)

---

### Phase 4: Lecture-wise Planning

**Framework:** None — direct LLM call
**Pattern:** Single structured output call

**What this phase does:**

Phase 4 takes the refined syllabus and the COs together and decides how the course content should be divided into individual lectures. It produces the lecture plan — the complete list of lectures with their assigned topics, subtopics, duration, and CO mappings.

**Why no framework:**

By the time Phase 4 runs, the what has been fully decided by Phases 1, 2, and 3. The syllabus defines all topics and subtopics. The COs define all learning objectives. Phase 4 is purely an allocation task — assigning content to time slots in a pedagogically sensible order. There is no reasoning uncertainty here that would benefit from an agent loop or a multi-step graph. A single well-prompted LLM call with a strict output schema will do this reliably.

**What the LLM decides:**

How many total lectures the course has (based on credit hours — typically one credit hour equals one 50-minute lecture). Which subtopics belong together in the same lecture. What the natural lecture title should be. How long each lecture should be (some topics need more time). Which COs and Sub-COs each lecture addresses. What the sequencing of lectures should be, which may differ slightly from the unit sequencing if pedagogical reasons warrant it.

**What Phase 4 produces:**

A JSON array where each element represents one lecture. Each lecture entry contains a lecture number, title, list of subtopics covered, estimated duration in minutes, list of COs and Sub-COs the lecture contributes to, and the domain context. This array is the direct input that drives all of Phase 5.

**Skills used in Phase 4:** None

**Tools used in Phase 4:** None

**MCP servers used in Phase 4:**
- PostgreSQL MCP — reads refined syllabus and COs, writes lecture plan array

---

### Phase 5a: PPT Generation

**Framework:** LangGraph
**Pattern:** Outline agent followed by dynamic parallel slide agents via LangGraph Send API, followed by assembly

**What this phase does:**

Phase 5a generates the complete presentation slides for every lecture in the course. Lectures are processed sequentially — Lecture 1 is fully completed before Lecture 2 begins, because lectures build on each other and later slide agents need to know what earlier lectures established.

Within each lecture, slide generation is partially parallel. The outline for the lecture is created first by a single agent that sees the full lecture plan. Then individual slide content is generated in parallel by multiple subagents, one per slide.

**The Slide Outline Agent:**

Before any slide content is generated, a single outline agent sees the complete lecture plan for that lecture. It decides how many slides the lecture needs, what each slide's title should be, what role each slide plays in the lecture narrative (introduction, concept definition, worked example, comparison, transition, summary), and which subtopic each slide covers. This outline is the structural decision for the entire lecture and it is made holistically, with full awareness of all subtopics, all COs the lecture addresses, and where this lecture sits in the overall course sequence.

This agent uses the Slide Structure Guidelines skill extensively. The skill tells it how many slides are appropriate for a given lecture duration, what roles are needed in a complete lecture, and what the difficulty escalation should look like. This agent does not write slide content — it only produces the plan that slide content agents will follow.

**Why the outline agent matters:**

If individual slide agents were spawned without a prior outline, each would make its own structural decisions. The result would be slides that are locally coherent but globally incoherent — no clear narrative, no sensible difficulty curve, inconsistent use of examples. The outline agent ensures that the structure of the lecture is decided once, by a single reasoning process with full context, and then the parallelism happens only at the content level within that decided structure.

**The Slide Content Agents (parallel, via Send API):**

Once the outline exists, LangGraph's Send API spawns one subagent per slide. These run in parallel. Each slide agent receives its specific slide outline entry, a summary of the previous slide's content (so it knows where the lecture is coming from), the title of the next slide (so it knows where the lecture is going), the CO and Sub-CO this slide contributes to, the course level, and the Slide Structure Guidelines skill.

The slide agent produces the content for its one slide: the slide title, the content blocks (bullet points, definitions, formulas, code snippets as appropriate for the domain), the speaker notes (the explanation the instructor would say aloud), and a visual suggestion describing what kind of diagram or image would enhance this slide.

**The Assembly and Consistency Check node:**

After all slide agents complete, their outputs are collected in slide order. The assembly node runs a consistency pass across the full lecture. It checks for terminology consistency (the same concept should be named the same way throughout), difficulty curve integrity (the progression of cognitive demand should be smooth), and narrative flow (the transition from each slide to the next should make sense). The Continuity Guidelines skill is used here. If the assembly node identifies inconsistencies, it makes targeted corrections — it does not regenerate slides, it adjusts specific inconsistent elements.

After assembly, the structured slide data is sent to the Document Generation MCP which renders the actual PPTX file. The file is stored in MinIO via the File System MCP.

**Skills used in Phase 5a:**
- Slide Structure Guidelines (outline agent and each slide content agent)
- Bloom's Taxonomy Reference (ensuring slide objectives align with CO Bloom's levels)
- Continuity Guidelines (assembly node)

**Tools available in Phase 5a:**
- Image/Diagram Search via Custom Tools MCP (slide agents decide whether to call it)

**MCP servers used in Phase 5a:**
- File System MCP — reads skill files, writes final PPTX to MinIO
- PostgreSQL MCP — reads lecture plan, writes structured PPT content
- Document Generation MCP — renders PPTX from structured content
- Custom Tools MCP — image and diagram search if invoked

---

### Phase 5b: Notes Generation

**Framework:** LangGraph
**Pattern:** Notes orchestrator followed by dynamic parallel subtopic notes agents via Send API, followed by assembly and QA gate

**What this phase does:**

Phase 5b generates the complete lecture notes for every lecture. Notes generation happens after PPT generation for each lecture because notes must expand on and align with what the slides cover. A student reading the notes should find that the notes explain in depth exactly what the slides present at a high level.

Like Phase 5a, lectures are processed sequentially. Within each lecture, subtopic notes are generated in parallel.

**Why subtopic-level parallelism (not slide-level):**

In Phase 5a, parallelism was at the slide level because a slide is the right unit of work — one slide, one agent. In Phase 5b, the right unit of work is a subtopic, not a slide. Lecture notes are long-form content. A single subtopic's notes can be 2,000 to 4,000 tokens of output covering explanations, examples, worked problems, and references. This is genuinely too large to produce for an entire lecture in one call without quality degradation. More importantly, subtopics are relatively self-contained in notes — each subtopic has its own explanation arc, its own examples, its own conclusion. This is different from slides, where each slide is a step in a continuous narrative. Subtopic notes can be generated in parallel and then assembled.

**The Notes Orchestrator:**

A single orchestrator node reads the complete PPT content for the lecture from Phase 5a's output in PostgreSQL. It packages the content into subtopic bundles — for each subtopic in the lecture, it collects the slides that cover that subtopic, the CO and Sub-CO the subtopic contributes to, the course level, and a summary of what the previous subtopic covered. These packages are the inputs to the individual subtopic notes agents.

**The Subtopic Notes Agents (parallel, via Send API):**

LangGraph's Send API spawns one agent per subtopic in the lecture. Each agent receives its subtopic package. It knows exactly which slides it is expanding (from the PPT content), what learning objective it is serving (from the Sub-CO), what the student already covered in the previous subtopic, and what depth level is appropriate (from the Academic Level Calibrator skill).

The agent generates long-form notes for its subtopic: a concept explanation that goes deeper than the slides, worked examples that illustrate the concept, connections to related concepts already covered earlier in the course, practice questions where appropriate, and references for further reading. The Bloom's Taxonomy Reference skill guides the depth — a subtopic serving an Analyze-level CO should have notes that develop analytical reasoning, not just description.

**The Notes Assembler:**

After all subtopic agents complete, the assembler collects their outputs in subtopic order and stitches them into a coherent lecture notes document. It adds transitions between subtopics — brief bridging paragraphs that connect the end of one subtopic to the beginning of the next. It runs a terminology consistency check using the Continuity Guidelines skill. It verifies that the difficulty progression across subtopics is sensible.

**The QA Gate:**

After assembly, a lightweight QA node performs two checks. First, it verifies that the assembled notes actually cover all the topics listed in the lecture plan — no subtopic should be missing or skimmed. Second, it calls the Plagiarism Checker via the Custom Tools MCP to verify originality. If the coverage check fails for any subtopic, only that subtopic's notes are regenerated — not the entire lecture. If the plagiarism check fails, the affected section is flagged for human review rather than automatic regeneration.

After the QA gate passes, the structured notes content is sent to the Document Generation MCP which renders both an MD file and a PDF. Both are stored in MinIO via the File System MCP.

**Skills used in Phase 5b:**
- Bloom's Taxonomy Reference (subtopic notes agents)
- Academic Level Calibrator (subtopic notes agents)
- Continuity Guidelines (notes assembler)

**Tools available in Phase 5b:**
- Plagiarism Checker via Custom Tools MCP (QA gate node, always called)
- Web Search (subtopic notes agents, if they need a current reference)

**MCP servers used in Phase 5b:**
- File System MCP — reads skill files, writes final notes files to MinIO
- PostgreSQL MCP — reads lecture plan and PPT content from Phase 5a
- Document Generation MCP — renders MD and PDF from assembled notes
- Custom Tools MCP — plagiarism check at QA gate

---

## How Data Flows Through the Entire System

This section traces a single course from input to output to show exactly what data exists at each stage and what consumes it.

A course coordinator uploads a curriculum MD file to MinIO. The pipeline is triggered with the file path and course code.

Phase 1 retrieves the file via File System MCP. The curriculum loader extracts course metadata using the Curriculum Parser Instructions skill. The expander uses the Academic Level Calibrator skill and optionally the Qdrant similarity search tool to expand the curriculum into a structured syllabus. After up to three critic cycles, the validated SyllabusDraft JSON is written to the syllabuses table in PostgreSQL via the PostgreSQL MCP.

Phase 2 reads the SyllabusDraft from PostgreSQL. Four evaluator nodes run in parallel. The Hours Evaluator calls the Credit Hour Calculator via Custom Tools MCP. The Relevance Evaluator queries the Reference Database MCP. The Aggregator writes a RefinedSyllabus JSON to PostgreSQL, noting which evaluators passed and any feedback applied.

Phase 3 reads the RefinedSyllabus from PostgreSQL. The PhiData agent loads the Bloom's Taxonomy Reference and Course Outcome Writing Guidelines skills via File System MCP. It optionally queries the Reference Database MCP. It writes a CourseOutcomes JSON to PostgreSQL — a list of COs and Sub-COs with full Bloom's mapping.

Phase 4 reads both the RefinedSyllabus and CourseOutcomes from PostgreSQL in a single call. It produces a LecturePlan JSON — an array of lecture objects — and writes it to PostgreSQL.

Phase 5a, for each lecture sequentially: reads the lecture's entry from the LecturePlan in PostgreSQL. Loads slide-related skills via File System MCP. The outline agent produces a SlideOutline. The Send API spawns slide content agents which may call the Image Search tool via Custom Tools MCP. The assembly node produces a StructuredPPTContent JSON which is written to PostgreSQL. The Document Generation MCP renders this to a PPTX file. The File System MCP stores the PPTX to MinIO.

Phase 5b, for each lecture sequentially after 5a: reads the lecture's entry from LecturePlan and the StructuredPPTContent from PostgreSQL. Loads notes-related skills via File System MCP. The orchestrator packages subtopic bundles. The Send API spawns subtopic notes agents which may call Web Search. The assembler produces AssembledNotes. The QA gate calls the Plagiarism Checker via Custom Tools MCP. The Document Generation MCP renders to MD and PDF. The File System MCP stores both files to MinIO.

At the end of all phases for a course, PostgreSQL contains the full structured record of every phase's output. MinIO contains the PPTX files and notes files. The pipeline run record in PostgreSQL stores phase statuses, iteration counts, and timestamps for full auditability.

---

## State Management Across Phases

Each phase has its own typed state object. The state is defined before any code is written for that phase. State fields are categorized as input fields (set at phase entry, never modified), working state fields (modified across agent iterations within a phase), and output fields (set only when the phase completes successfully).

The inter-phase data store is PostgreSQL. Phase N does not keep Phase N-1's output in memory — it reads it fresh from the database at startup. This means phases are independently restartable. If Phase 3 fails, it can be restarted without rerunning Phases 1 and 2, because their outputs are persisted in PostgreSQL. This is critical for a 200-course production system where failures will occur.

---

## The Dependency Injection Pattern

Every external dependency in every phase is accessed through an abstract interface. Interfaces define what operations are available (read a curriculum file, write a syllabus, load a skill). Mock implementations fulfill these interfaces using local files and local JSON outputs. Real implementations fulfill these interfaces using actual MCP servers.

The factory functions that return the correct implementation based on a configuration flag (mock vs real) are the only place in the system where this choice is made. Every node, every graph, every phase works identically regardless of whether mocks or real implementations are active. This means the entire pipeline can be developed, tested, and validated on a laptop with no infrastructure, and then moved to the DGX cluster with MCP servers simply by changing an environment variable.

---

## Quality and Observability

Every LLM call, every node execution, every tool invocation is traced via LangSmith for LangGraph phases and PhiData's built-in observability for Phase 3. Every phase writes its status, iteration count, and output metadata to PostgreSQL alongside the structured output. Every PPTX and notes file is stored with a metadata record linking it to the course code, lecture number, and the phase run that produced it.

Quality gates exist at three points: the Gap Critic in Phase 1 (content correctness), the four evaluators in Phase 2 (fitness quality), and the QA gate in Phase 5b (coverage and originality). Each quality gate produces a structured evaluation report stored in PostgreSQL for review.

---

## What Is Not in This System

There is no conversational interface in this pipeline. There is no chatbot, no user-facing query loop. The pipeline is triggered with a curriculum file path and course code, and it runs to completion producing files. Any user-facing interface that allows browsing, editing, or requesting regeneration of specific outputs is a separate system built on top of this pipeline's PostgreSQL and MinIO outputs.

There is no fine-tuning in Phase 1 through 4. The system uses capable base models served via vLLM. Fine-tuning may be added later once the pipeline has processed enough courses to have a quality dataset, but it is not part of the initial design.

There is no human-in-the-loop step within the pipeline itself. The pipeline runs fully automated. Human review happens after the pipeline completes by examining the outputs. If a human reviewer identifies a quality issue in the generated syllabus or COs, they can edit the PostgreSQL record and re-trigger the downstream phases from that point.
