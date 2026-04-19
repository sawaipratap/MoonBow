# Academic Level Calibrator Skill

## Purpose

This skill guides you in calibrating the depth, complexity, vocabulary, and scope of any educational content — syllabus subtopics, Course Outcomes, lecture notes, or slide objectives — to the correct academic level. You must check `course_level` in the course metadata before applying any of these guidelines. Every content decision you make — depth of a subtopic, the Bloom's level of a CO, the complexity of an explanation in notes — must be filtered through the lens of the stated course level.

---

## Level Definitions

### Undergraduate (UG)

**Target student:** Has 1–3 years of higher education. Has completed introductory courses in the domain. Can apply concepts but has limited theoretical depth.

**Depth:**
- Conceptual understanding with practical application.
- Cover the "what" and "how" thoroughly. The "why" is introduced but not required at research depth.
- Avoid excessive theoretical abstraction. Derivations are introduced, not mastered.
- Edge cases are acknowledged but not the focus.

**Vocabulary:**
- Use standard domain terminology consistently.
- Define all jargon when first introduced.
- Abbreviations must be expanded on first use.
- Avoid research-paper-level terminology without explanation.

**Subtopic structure:**
- Cover fundamentals thoroughly before any advanced application.
- Each subtopic should be independently understandable given the prior subtopics in the same course.
- Worked examples are essential for every non-trivial concept.

**Estimated subtopic hours:** 1–3 hours per subtopic.

**Expected prior knowledge:**
- Basic mathematics (calculus, linear algebra, probability at an introductory level).
- Introductory domain concepts from explicitly listed prerequisite courses.
- Do not assume knowledge not listed in the course prerequisites.

**What UG content must NOT do:**
- Reference open research problems as content targets.
- Assume familiarity with primary literature (papers, conference proceedings).
- Require students to synthesize methodologies not previously introduced.

---

### Postgraduate (PG)

**Target student:** Has completed a bachelor's degree in the domain or a closely related field. Has solid foundational knowledge. Is capable of independent study.

**Depth:**
- Deep theoretical grounding with research awareness.
- Students must understand not just how but why — the mathematical foundations, the failure modes, the design decisions behind methods.
- Cover state-of-the-art techniques alongside foundational theory.
- Include open problems or active research directions where relevant to the course.

**Vocabulary:**
- Advanced domain terminology is assumed to be known.
- Introduce research-level concepts with precise definitions.
- Engage with the vocabulary used in relevant recent literature.

**Subtopic structure:**
- Start from a brief foundation recap (do not re-teach UG material at length).
- Develop theoretical rigour quickly.
- Include critical analysis of methods — trade-offs, limitations, comparisons to alternatives.

**Estimated subtopic hours:** 2–5 hours per subtopic.

**Expected prior knowledge:**
- Strong domain foundation equivalent to a bachelor's degree in the field.
- Basic research methodology — reading papers, identifying hypotheses, understanding experimental evaluation.
- Mathematical maturity: comfort with proofs, formal notation, and mathematical reasoning.

**What PG content must NOT do:**
- Treat students as beginners who need concept definitions from scratch.
- Avoid theoretical foundations by staying surface-level.
- Ignore existing literature or frame the domain as if no prior work exists.

---

### PhD

**Target student:** Has a master's degree or equivalent in the domain. Is an active or aspiring researcher. Is capable of and expected to engage with primary literature.

**Depth:**
- Research-level treatment throughout.
- Emphasis on limitations of current methods, open problems, methodological nuance, and research frontiers.
- Broad survey of the landscape, with deep specialization in selected areas.
- Students must be equipped to identify a research question within each covered area.

**Vocabulary:**
- Cutting-edge terminology used precisely.
- Primary literature vocabulary is the baseline.
- Neologisms and emerging terminology from recent conferences and preprints are appropriate.

**Subtopic structure:**
- Each subtopic is a door to a research area, not a self-contained unit.
- Connections across subtopics and to external literature are explicit.
- Subtopics include at least one reference to a pivotal primary work, survey paper, or benchmark in the area.

**Estimated subtopic hours:** 3–8 hours per subtopic, depending on breadth of the research area.

**Expected prior knowledge:**
- Mastery of domain fundamentals. No re-teaching.
- Familiarity with the major research venues in the domain (conferences, journals).
- Prior exposure to research methodology: reading, critiquing, and situating papers in broader literature.

**What PhD content must NOT do:**
- Spend time on foundational definitions that any PhD candidate in the field would know.
- Treat topics as settled when there is active debate in the literature.
- Omit discussion of failure modes, assumptions, and limitations.

---

## Calibration Checklist

Before finalising any subtopic expansion, Course Outcome, or notes section, run through this checklist mentally:

1. **Level match:** Is the depth appropriate for the stated course level? Would a student at this level be challenged but not overwhelmed?
2. **Hours realism:** Are the estimated hours realistic for the depth described? (UG: 1–3h, PG: 2–5h, PhD: 3–8h per subtopic)
3. **Prior knowledge assumption:** Does this content assume only what the student at this level would actually have? Are prerequisites from the course metadata the only assumptions being made?
4. **Vocabulary consistency:** Is the vocabulary consistent with the level throughout? No sudden jumps to PhD terminology in a UG course or unnecessary simplification in a PG course.
5. **Theoretical-practical balance:** Is the balance between theory and application appropriate for the level? (UG: practical-leaning, PG: balanced, PhD: theory/research-leaning)

---

## Common Calibration Errors to Avoid

| Error | Example | Correct Approach |
|---|---|---|
| UG content too abstract | Explaining gradient descent using measure theory | Use geometric intuition and numerical examples |
| PG content too shallow | Treating all PG subtopics as "introductory overview" | Include theoretical grounding and comparative analysis |
| PhD content re-teaching basics | Starting a PhD CV course with pixel fundamentals | Start at feature learning and above |
| Hour allocation not matching depth | "3-hour" subtopic described in 1 sentence | Hours must match the described scope and depth |
| Wrong prior knowledge assumption | Assuming UG students know Bayesian inference when it is not in prerequisites | Explicitly cover assumed knowledge or remove assumption |
