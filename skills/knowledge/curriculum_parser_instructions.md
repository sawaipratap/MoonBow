# Curriculum Parser Instructions Skill

## Purpose

This skill guides you in extracting structured, consistent information from raw curriculum documents. Curriculum documents arrive in many formats — some are well-structured with clear unit headings and numbered topics, some are dense paragraphs, some have inconsistent numbering, abbreviations, duplicate entries, or vague placeholder entries like "Advanced Topics". Your job is to produce a clean, structured output regardless of how the input is formatted.

This skill is used in the curriculum loading step at the start of Phase 1, before expansion begins. The structured metadata and topic groupings you produce here are the foundation that the Expander node works from.

---

## What to Extract

From any curriculum document, identify and extract the following. Apply the handling rules below for each field when the information is not clearly stated.

### 1. Course Name
The full official name of the course. Not an abbreviation. Strip any catalogue-style formatting (e.g., "CSE 301: Data Structures and Algorithms" → course name is "Data Structures and Algorithms").

### 2. Course Code
The alphanumeric identifier (e.g., "CSE2001", "ME401"). If the document uses multiple formats, prefer the one in the course header over in-body references.

### 3. Academic Level
One of: `UG`, `PG`, or `PhD`.

**Inference rules when not explicitly stated:**
- Course codes ending in 1xx–4xx with no further prefix → UG
- Course codes ending in 5xx–6xx, or with a "P" or "M" prefix → PG
- Courses listed under "Doctoral Programme" headings → PhD
- If year of study is mentioned: Year 1–3 → UG, Year 4+ or "Final Year Masters" → PG
- Syllabi that reference "literature review", "research proposal", or "dissertation" → PhD

### 4. Credit Hours
The number of academic credit units. May appear as "credits", "units", "contact hours", "L-T-P" (Lecture-Tutorial-Practical), or similar.

**Inference rules when not stated:**
- Count the number of major units and apply typical university credit structures: 3–4 units → 3 credits, 5+ units → typically 4 credits
- If a total hours figure is given (e.g., "45 hours"), divide by 15 to estimate credits

### 5. Prerequisites
Courses or knowledge areas listed as requirements for enrolling in this course. May appear as "Prerequisites:", "Pre-requisites:", or inline ("assumes knowledge of...").

**Rules:**
- List only what is explicitly stated. Do not invent prerequisites based on topic inference.
- If none are listed, return an empty array. Never populate prerequisites by assumption.

### 6. Units / Modules
The top-level divisions of the course. May be called "Unit", "Module", "Part", "Section", or "Chapter".

**Rules:**
- Assign sequential integer unit numbers (Unit 1, Unit 2, ...) regardless of how the source numbers them (Roman numerals, letters, etc.).
- If no explicit unit grouping exists and only a flat topic list is given, group logically related topics into units. Use domain logic to determine groupings. Never create a unit with only one topic if it can be reasonably combined with an adjacent related unit.

### 7. Topics Within Each Unit
The specific subject matter listed under each unit or inferred from a flat topic list.

**Rules:**
- Preserve the topic names as stated, unless they require expansion (see abbreviation rules below).
- Do not add topics that are not mentioned anywhere in the document — the Expander handles gap-filling.
- If a topic appears under multiple units, keep only the first occurrence and note the duplication in the output.

### 8. Time Allocations Per Unit
If the document provides hours or session counts per unit, capture them. These will be used by the Expander to calibrate subtopic hours.

---

## Handling Common Formatting Problems

### Roman Numerals
Convert to integers.
- `Unit I` → Unit 1, `Unit IV` → Unit 4
- `Module II` → Unit 2

### Abbreviations
Expand where the full form is known and unambiguous. Examples:
- `ML` → `Machine Learning`  
- `NLP` → `Natural Language Processing`  
- `OS` → `Operating Systems`  
- `DS` → `Data Structures`  
- `DB` or `DBMS` → `Database Management Systems`

**Rule:** If an abbreviation is ambiguous (e.g., `PL` could mean "Programming Languages" or "Propositional Logic"), leave it as stated and flag it. Do not guess.

### Duplicate Topics
If the same topic name or a clearly redundant topic (same content described differently) appears in more than one unit:
- Keep only the first occurrence.
- In the structured output, note: `"duplicate_of": "Unit N, Topic Name"` on the second occurrence so the Expander is aware.

### Vague or Placeholder Topics
Entries like "Advanced Topics", "Miscellaneous", "Special Topics", "Case Studies", "Recent Advances" are common in raw curricula. They are intentionally vague.
- Keep them as-is in the topic list.
- Flag them with: `"requires_expansion_flag": true`
- The Expander will handle expansion of these entries based on domain context.

### L-T-P Credit Notation
Some engineering curricula use L-T-P (Lecture-Tutorial-Practical) notation, e.g., `3-1-0` or `L:3 T:1 P:0`.
- Credit hours = L (lecture hours per week) × 15 weeks (standard semester).
- A `3-1-0` structure → 3 lecture hours/week → 45 hours → 3 credits.
- A `3-0-2` structure → 3 lecture + 1 practical → treat as 4 credits if so stated, otherwise 3.

### Missing Unit Structure (Flat Topic List)
When the curriculum is just a list of topics with no unit headings:
1. Group topics by thematic or logical domain.
2. Assign each group a unit number and a descriptive unit name.
3. Aim for 3–7 topics per unit. Do not create units with only 1–2 topics unless the topic is clearly large enough to stand alone (e.g., "Introduction to Machine Learning" at PG level).
4. Order units from foundational to advanced wherever possible.

---

## Output Contract

Always return structured data. Never return the raw curriculum text unchanged. The structured output you produce must conform to the CourseMetadata and Topic schemas defined in Phase 1's state model.

Specifically, your output must contain:
- `course_name`: string
- `course_code`: string
- `course_level`: "UG" | "PG" | "PhD"
- `credit_hours`: integer
- `domain`: string (the academic/engineering domain — e.g., "Computer Science", "Electrical Engineering", "Biotechnology")
- `institution`: string (if stated; else empty string)
- `semester`: string (if stated; else empty string)
- `prerequisites`: list of strings (empty list if none stated)
- `units`: list of unit objects, each with:
  - `unit_number`: integer
  - `unit_name`: string
  - `topics`: list of topic strings
  - `stated_hours`: float or null (if given in the source document)
  - `flags`: list of strings (e.g., `"has_vague_entry"`, `"has_duplicate"`) — empty list if none

---

## Quality Rules

1. **Do not invent.** If information is not in the document, leave the field empty or as a reasonable default. The only exception is grouping flat topic lists into units — that requires judgement, not invention.
2. **Do not merge distinct units.** If the source has 6 clearly distinct units, do not collapse them into 4 for tidiness.
3. **Do not reorder topics within a unit.** Preserve the sequence as given — the Gap Critic will identify sequencing problems, not the parser.
4. **Flag, do not decide.** If something is ambiguous (e.g., an abbreviation, a vague topic), flag it. The Expander or a human reviewer will decide.
5. **Determinism.** Given the same input document, always produce the same structured output. Do not introduce variation based on phrasing of your explanation.
