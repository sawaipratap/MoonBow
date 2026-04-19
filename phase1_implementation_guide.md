# Phase 1 — Curriculum to Syllabus Expansion
## Complete Implementation Guide for Coding Agent

---

## Context and Purpose

This document is a complete implementation guide for Phase 1 of an educational content generation pipeline. Phase 1 takes a raw curriculum document (MD or PDF) and expands it into a detailed, structured syllabus using a LangGraph-based Generator-Critic cycle.

**What Phase 1 produces** is consumed directly by Phase 2 (Syllabus Refinement). The output must be a structured JSON object written to PostgreSQL. Since the DB, MCP servers, and skill files are not yet built, this implementation uses interfaces and mocks so that real implementations can be swapped in with zero changes to graph code.

**Do not deviate from the project structure defined in this document.** Every file path, class name, and interface contract is intentional and will be referenced by other phases and team members.

---

## Technology Stack

- **Python 3.11+**
- **LangGraph** — graph orchestration
- **LangChain** — LLM abstraction layer (used inside nodes)
- **Pydantic v2** — state schema and structured output validation
- **vLLM or LiteLLM** — LLM backend (configured via environment variable, not hardcoded)
- **python-dotenv** — environment configuration
- **pytest** — testing

Install dependencies:
```bash
pip install langgraph langchain langchain-core pydantic python-dotenv pytest
```

---

## Project Structure

Create exactly this directory and file structure. Every file listed must be created.

```
phase1/
│
├── state.py
│
├── interfaces/
│     ├── __init__.py
│     ├── file_reader.py
│     ├── db_writer.py
│     ├── skill_loader.py
│     └── tool_runner.py
│
├── mocks/
│     ├── __init__.py
│     ├── mock_file_reader.py
│     ├── mock_db_writer.py
│     ├── mock_skill_loader.py
│     └── mock_tool_runner.py
│
├── skills/
│     ├── academic_level_calibrator.md
│     └── curriculum_parser_instructions.md
│
├── prompts/
│     ├── expander_prompt.md
│     └── gap_critic_prompt.md
│
├── nodes/
│     ├── __init__.py
│     ├── curriculum_loader.py
│     ├── skill_injector.py
│     ├── expander.py
│     ├── gap_critic.py
│     └── output_writer.py
│
├── graph.py
│
├── config.py
│
├── test_data/
│     ├── sample_curriculum.md
│     └── expected_output_schema.json
│
└── tests/
      ├── __init__.py
      ├── test_state.py
      ├── test_nodes.py
      └── test_graph.py
```

---

## Step 1 — config.py

This is the single source of configuration. All environment variables and constants are read here. No other file reads from environment directly.

```python
# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM settings
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://192.168.1.13:8000/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "dummy")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "meta-llama/Llama-3.1-70B-Instruct")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # Graph settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))

    # Dependency mode — switch between mock and real implementations
    # Set to "mock" during development, "real" when MCP and DB are ready
    DEPENDENCY_MODE: str = os.getenv("DEPENDENCY_MODE", "mock")

    # Paths (used by mocks)
    TEST_DATA_DIR: str = os.path.join(os.path.dirname(__file__), "test_data")
    SKILLS_DIR: str = os.path.join(os.path.dirname(__file__), "skills")
    PROMPTS_DIR: str = os.path.join(os.path.dirname(__file__), "prompts")
    MOCK_OUTPUT_DIR: str = os.path.join(os.path.dirname(__file__), "mock_outputs")

config = Config()
```

---

## Step 2 — state.py

This is the most critical file. Define this before writing any node. The state is the contract between all nodes in the graph. Every field must have a clear type and purpose.

```python
# state.py

from typing import Optional, Annotated
from pydantic import BaseModel, Field
import operator


# --- Sub-schemas used within state ---

class CourseMetadata(BaseModel):
    course_name: str
    course_code: str
    course_level: str                   # "UG" | "PG" | "PhD"
    credit_hours: int
    domain: str                         # e.g. "Computer Science", "Mechanical Engineering"
    institution: str
    semester: str                       # e.g. "Semester 4"
    prerequisites: list[str] = []       # list of prerequisite course names


class Subtopic(BaseModel):
    subtopic_name: str
    depth_level: str                    # "introductory" | "intermediate" | "advanced"
    estimated_hours: float
    description: str
    prerequisites_within_course: list[str] = []  # subtopics that must come before this


class Topic(BaseModel):
    topic_name: str
    unit_number: int
    subtopics: list[Subtopic]
    total_hours: float
    learning_intent: str                # what the student should understand after this unit


class SyllabusDraft(BaseModel):
    course_metadata: CourseMetadata
    topics: list[Topic]
    total_hours: float
    coverage_summary: str               # one paragraph describing what the course covers


class CriticGap(BaseModel):
    gap_type: str                       # "missing_prerequisite" | "coverage_gap" | "sequencing_issue" | "depth_mismatch"
    location: str                       # which topic/subtopic the gap is in
    description: str                    # specific description of the problem
    suggested_fix: str                  # what the expander should do to fix it


class CriticFeedback(BaseModel):
    has_gaps: bool
    gaps: list[CriticGap]
    overall_assessment: str             # one paragraph summary of the evaluation
    confidence_score: float             # 0.0 to 1.0 — critic's confidence in its evaluation


# --- Main LangGraph State ---

class Phase1State(BaseModel):
    # Input fields — set at graph entry, never modified
    curriculum_raw: str = ""                            # raw text extracted from curriculum file
    curriculum_file_path: str = ""                      # original file path
    course_metadata: Optional[CourseMetadata] = None   # parsed from curriculum

    # Injected skill context — set by skill_injector node
    level_calibrator_skill: str = ""                    # contents of academic_level_calibrator.md
    parser_instructions_skill: str = ""                 # contents of curriculum_parser_instructions.md

    # Working state — modified across iterations
    syllabus_draft: Optional[SyllabusDraft] = None      # current expanded syllabus
    critic_feedback: Optional[CriticFeedback] = None    # latest critic evaluation
    iteration_count: int = 0                            # current loop count
    iteration_max: int = 3                              # max loops before force-pass

    # Expander context — what the expander receives each iteration
    expander_context: str = ""                          # formatted prompt context for expander

    # Tool results — populated if similarity search was invoked
    similar_topics_found: list[dict] = []               # topics found in other courses via Qdrant

    # Output fields — set by output_writer node
    syllabus_final: Optional[SyllabusDraft] = None
    phase_status: str = ""                              # "passed" | "force_passed" | "failed"
    phase_error: str = ""                               # error message if phase fails unexpectedly

    class Config:
        arbitrary_types_allowed = True
```

**Important notes on state design:**
- Every node receives the full state and returns a dict of only the fields it modifies
- Nodes must never modify input fields (`curriculum_raw`, `curriculum_file_path`)
- `iteration_count` is incremented only inside the router, not inside nodes
- `phase_status` is set only by `output_writer`

---

## Step 3 — Interfaces

These are abstract base classes. Every external dependency has one. Nodes import and use these — never the mock or real implementation directly.

### interfaces/file_reader.py

```python
# interfaces/file_reader.py

from abc import ABC, abstractmethod


class FileReader(ABC):
    """
    Abstract interface for reading curriculum files.
    Implementations: MockFileReader (development), MCPFileReader (production).
    """

    @abstractmethod
    def read_curriculum(self, file_path: str) -> str:
        """
        Read a curriculum file and return its full text content.
        
        Args:
            file_path: Path or URI to the curriculum file (MD or PDF)
        
        Returns:
            Full text content of the curriculum as a string.
            PDF files must be extracted to plain text before returning.
        
        Raises:
            FileNotFoundError: if the file does not exist
            ValueError: if the file format is not supported
        """
        pass

    @abstractmethod
    def read_skill(self, skill_name: str) -> str:
        """
        Read a skill MD file by name.
        
        Args:
            skill_name: filename without path, e.g. "academic_level_calibrator.md"
        
        Returns:
            Full text content of the skill file.
        
        Raises:
            FileNotFoundError: if the skill file does not exist
        """
        pass
```

### interfaces/db_writer.py

```python
# interfaces/db_writer.py

from abc import ABC, abstractmethod
from state import SyllabusDraft, Phase1State


class DBWriter(ABC):
    """
    Abstract interface for writing Phase 1 outputs to persistent storage.
    Implementations: MockDBWriter (development), MCPPostgresWriter (production).
    """

    @abstractmethod
    def write_syllabus(
        self,
        syllabus: SyllabusDraft,
        course_code: str,
        phase_status: str,
        iteration_count: int
    ) -> str:
        """
        Write the final syllabus to the database.
        
        Args:
            syllabus: The validated SyllabusDraft object
            course_code: Unique course identifier
            phase_status: "passed" | "force_passed"
            iteration_count: How many iterations were needed
        
        Returns:
            Record ID of the written syllabus (str UUID or DB-generated ID)
        
        Raises:
            ConnectionError: if DB connection fails
            ValueError: if syllabus fails schema validation
        """
        pass

    @abstractmethod
    def check_syllabus_exists(self, course_code: str) -> bool:
        """
        Check if a syllabus already exists for this course code.
        Used to avoid reprocessing.
        
        Args:
            course_code: Unique course identifier
        
        Returns:
            True if syllabus exists, False otherwise
        """
        pass
```

### interfaces/skill_loader.py

```python
# interfaces/skill_loader.py

from abc import ABC, abstractmethod


class SkillLoader(ABC):
    """
    Abstract interface for loading skill MD files into agent context.
    Implementations: MockSkillLoader (development), MCPSkillLoader (production).
    
    Skills are MD files that contain domain knowledge injected into LLM context
    before reasoning begins. They are not tools — they are read once and used
    as part of the system/user prompt.
    """

    @abstractmethod
    def load(self, skill_name: str) -> str:
        """
        Load a skill MD file by name and return its full content.
        
        Args:
            skill_name: Skill filename without path.
                        e.g. "academic_level_calibrator.md"
                             "curriculum_parser_instructions.md"
        
        Returns:
            Full markdown content of the skill file as a string.
        
        Raises:
            FileNotFoundError: if the skill does not exist
        """
        pass

    @abstractmethod
    def list_available_skills(self) -> list[str]:
        """
        Return a list of all available skill file names.
        Used for validation and debugging.
        """
        pass
```

### interfaces/tool_runner.py

```python
# interfaces/tool_runner.py

from abc import ABC, abstractmethod


class ToolRunner(ABC):
    """
    Abstract interface for tools available to agents during reasoning.
    Tools are different from skills — the agent decides whether to call
    them based on what it encounters during reasoning.
    
    Phase 1 has one tool: similarity search across other course curricula.
    Implementations: MockToolRunner (development), MCPToolRunner (production).
    """

    @abstractmethod
    def run_similarity_search(
        self,
        topics: list[str],
        top_k: int = 5
    ) -> list[dict]:
        """
        Search across the cross-curriculum Qdrant index for similar topics
        in other courses. Used by the expander when uncertain whether a topic
        is already covered in a prerequisite course.
        
        Args:
            topics: List of topic names to search for
            top_k: Number of similar results to return per topic
        
        Returns:
            List of dicts: [
                {
                    "topic": str,
                    "course_code": str,
                    "course_name": str,
                    "similarity_score": float,
                    "coverage_level": str
                }
            ]
        
        Raises:
            ConnectionError: if Qdrant is unreachable
        """
        pass
```

---

## Step 4 — Mock Implementations

Mocks exist so the graph can run end-to-end before real dependencies are built. They must match the interface contracts exactly.

### mocks/mock_file_reader.py

```python
# mocks/mock_file_reader.py

import os
from interfaces.file_reader import FileReader
from config import config


class MockFileReader(FileReader):
    """
    Reads curriculum files from local test_data directory.
    Reads skill files from local skills directory.
    Used during development when MCP File System server is not available.
    """

    def read_curriculum(self, file_path: str) -> str:
        # If an absolute path is given, use it directly
        if os.path.isabs(file_path) and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        # Otherwise look in test_data directory
        local_path = os.path.join(config.TEST_DATA_DIR, os.path.basename(file_path))
        if not os.path.exists(local_path):
            raise FileNotFoundError(
                f"MockFileReader: curriculum file not found at {local_path}. "
                f"Place your test curriculum in {config.TEST_DATA_DIR}/"
            )
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()

    def read_skill(self, skill_name: str) -> str:
        skill_path = os.path.join(config.SKILLS_DIR, skill_name)
        if not os.path.exists(skill_path):
            raise FileNotFoundError(
                f"MockFileReader: skill file not found at {skill_path}. "
                f"Create the skill file at {config.SKILLS_DIR}/{skill_name}"
            )
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
```

### mocks/mock_db_writer.py

```python
# mocks/mock_db_writer.py

import os
import json
from datetime import datetime
from interfaces.db_writer import DBWriter
from state import SyllabusDraft
from config import config


class MockDBWriter(DBWriter):
    """
    Writes syllabus output to a local JSON file instead of PostgreSQL.
    Used during development when MCP PostgreSQL server is not available.
    Output location: mock_outputs/syllabus_{course_code}_{timestamp}.json
    """

    def __init__(self):
        os.makedirs(config.MOCK_OUTPUT_DIR, exist_ok=True)

    def write_syllabus(
        self,
        syllabus: SyllabusDraft,
        course_code: str,
        phase_status: str,
        iteration_count: int
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        record_id = f"mock_{course_code}_{timestamp}"

        output = {
            "record_id": record_id,
            "course_code": course_code,
            "phase_status": phase_status,
            "iteration_count": iteration_count,
            "written_at": timestamp,
            "syllabus": syllabus.model_dump()
        }

        output_path = os.path.join(
            config.MOCK_OUTPUT_DIR,
            f"syllabus_{record_id}.json"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        print(f"[MockDBWriter] Syllabus written to {output_path}")
        return record_id

    def check_syllabus_exists(self, course_code: str) -> bool:
        # Check if any output file exists for this course code
        if not os.path.exists(config.MOCK_OUTPUT_DIR):
            return False
        existing = [
            f for f in os.listdir(config.MOCK_OUTPUT_DIR)
            if course_code in f
        ]
        return len(existing) > 0
```

### mocks/mock_skill_loader.py

```python
# mocks/mock_skill_loader.py

import os
from interfaces.skill_loader import SkillLoader
from config import config


class MockSkillLoader(SkillLoader):
    """
    Loads skill MD files from local skills directory.
    In production, this will be replaced by MCPSkillLoader which
    reads from MinIO/S3 via the File System MCP server.
    """

    def load(self, skill_name: str) -> str:
        skill_path = os.path.join(config.SKILLS_DIR, skill_name)
        if not os.path.exists(skill_path):
            raise FileNotFoundError(
                f"MockSkillLoader: skill not found: {skill_path}\n"
                f"Create the file at {config.SKILLS_DIR}/{skill_name}"
            )
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_available_skills(self) -> list[str]:
        if not os.path.exists(config.SKILLS_DIR):
            return []
        return [
            f for f in os.listdir(config.SKILLS_DIR)
            if f.endswith(".md")
        ]
```

### mocks/mock_tool_runner.py

```python
# mocks/mock_tool_runner.py

from interfaces.tool_runner import ToolRunner


class MockToolRunner(ToolRunner):
    """
    Returns empty results for all tool calls.
    In production, this will be replaced by MCPToolRunner which
    connects to Qdrant via MCP for similarity search.
    """

    def run_similarity_search(
        self,
        topics: list[str],
        top_k: int = 5
    ) -> list[dict]:
        # Return empty list — no cross-curriculum data available in mock mode
        # The expander node must handle empty results gracefully
        print(f"[MockToolRunner] Similarity search called for {len(topics)} topics — returning empty (mock mode)")
        return []
```

---

## Step 5 — Dependency Injection Factory

This is the file that decides which implementation to use based on `DEPENDENCY_MODE` in config. Nodes import from here — they never import from mocks or real implementations directly.

```python
# dependencies.py

from config import config
from interfaces.file_reader import FileReader
from interfaces.db_writer import DBWriter
from interfaces.skill_loader import SkillLoader
from interfaces.tool_runner import ToolRunner


def get_file_reader() -> FileReader:
    if config.DEPENDENCY_MODE == "mock":
        from mocks.mock_file_reader import MockFileReader
        return MockFileReader()
    else:
        # When MCP is ready, implement and import MCPFileReader here
        raise NotImplementedError("MCPFileReader not yet implemented")


def get_db_writer() -> DBWriter:
    if config.DEPENDENCY_MODE == "mock":
        from mocks.mock_db_writer import MockDBWriter
        return MockDBWriter()
    else:
        raise NotImplementedError("MCPPostgresWriter not yet implemented")


def get_skill_loader() -> SkillLoader:
    if config.DEPENDENCY_MODE == "mock":
        from mocks.mock_skill_loader import MockSkillLoader
        return MockSkillLoader()
    else:
        raise NotImplementedError("MCPSkillLoader not yet implemented")


def get_tool_runner() -> ToolRunner:
    if config.DEPENDENCY_MODE == "mock":
        from mocks.mock_tool_runner import MockToolRunner
        return MockToolRunner()
    else:
        raise NotImplementedError("MCPToolRunner not yet implemented")
```

---

## Step 6 — Skill Files

Create these MD files in the `skills/` directory. These are read by the `skill_injector` node and injected into the LLM context. Write them carefully — they directly affect output quality.

### skills/academic_level_calibrator.md

```markdown
# Academic Level Calibrator Skill

## Purpose
This skill guides you in calibrating the depth, complexity, and vocabulary of syllabus content to the appropriate academic level. Always check course_level in the course metadata before applying these guidelines.

## Level Definitions

### Undergraduate (UG)
- **Depth:** Conceptual understanding with practical application. Avoid excessive theoretical abstraction.
- **Vocabulary:** Standard domain terminology. Define jargon when first introduced.
- **Subtopic depth:** Cover fundamentals thoroughly before edge cases.
- **Expected prior knowledge:** Basic mathematics, introductory domain concepts from prerequisite courses.
- **Estimated subtopic hours:** 1-3 hours per subtopic.

### Postgraduate (PG)
- **Depth:** Deep theoretical grounding with research awareness. Students should understand not just how but why.
- **Vocabulary:** Advanced domain terminology assumed known. Introduce research-level concepts.
- **Subtopic depth:** Cover state-of-the-art alongside fundamentals. Include open problems where relevant.
- **Expected prior knowledge:** Strong domain foundation, basic research methodology.
- **Estimated subtopic hours:** 2-5 hours per subtopic.

### PhD
- **Depth:** Research-level treatment. Emphasis on limitations, open problems, and methodological nuance.
- **Vocabulary:** Cutting-edge terminology. Engage with primary literature.
- **Subtopic depth:** Survey breadth with deep specialization in key areas.
- **Expected prior knowledge:** Mastery of domain fundamentals, prior research exposure.
- **Estimated subtopic hours:** 3-8 hours per subtopic.

## Calibration Checklist
Before finalizing any subtopic, ask:
1. Is the depth appropriate for the stated course level?
2. Are the estimated hours realistic given the depth?
3. Does the description assume the correct level of prior knowledge?
4. Is the vocabulary consistent with the level throughout?
```

### skills/curriculum_parser_instructions.md

```markdown
# Curriculum Parser Instructions Skill

## Purpose
This skill guides you in extracting structured information from raw curriculum text. Curricula are often inconsistently formatted. Apply these rules to produce clean, structured output regardless of input format.

## What to Extract
From any curriculum document, identify and extract:

1. **Course name and code** — usually in the header or title
2. **Credit hours** — may be listed as "credits", "units", "contact hours"
3. **Course level** — UG/PG/PhD, or infer from year of study if not stated
4. **Prerequisites** — may be listed explicitly or referenced in the course description
5. **Units/Modules** — the top-level divisions of the course
6. **Topics within each unit** — specific subject matter listed under each unit
7. **Any time allocations** — hours per unit if mentioned

## Handling Missing Information
- If credit hours are not stated, infer from number of topics and typical course structure
- If level is not stated, infer from course code (100-level = UG year 1, 400-level = UG year 4, 500+ = PG)
- If prerequisites are not listed, note them as empty — do not invent them
- If unit structure is absent and only a flat topic list is given, group related topics into logical units

## Common Formatting Problems and How to Handle Them
- **Roman numerals for units:** Convert to integers (Unit I → Unit 1)
- **Abbreviations:** Expand where the full form is known (ML → Machine Learning)
- **Duplicate topics:** If the same topic appears in multiple units, keep only the first occurrence and note the duplication
- **Vague entries like "Advanced topics":** Keep as-is but flag for expansion in the Expander node

## Output Contract
Always return a structured representation. Never return the raw text unchanged.
```

---

## Step 7 — Prompt Files

Write these in the `prompts/` directory. Prompts are MD files — nodes read them and format them with state values before calling the LLM. Test these prompts independently before integrating into nodes.

### prompts/expander_prompt.md

```markdown
# Expander System Prompt

You are an expert academic curriculum designer. Your task is to take a raw course curriculum and expand it into a detailed, structured syllabus.

## Your Inputs
You will receive:
- **Course metadata:** name, code, level (UG/PG/PhD), credit hours, domain, prerequisites
- **Raw curriculum text:** the original curriculum document content
- **Academic Level Calibrator skill:** guidelines for calibrating depth to the course level
- **Critic feedback (if this is a refinement iteration):** specific gaps identified in your previous expansion

## Your Task
Expand the curriculum into a structured syllabus with the following for each unit:
- A clear unit name and number
- 3 to 7 subtopics per unit
- For each subtopic: name, depth level, estimated hours, description, intra-course prerequisites
- A learning intent statement for each unit (what students should understand after completing it)
- A coverage summary paragraph for the entire course

## Rules
1. Do not invent topics that are not implied by the curriculum. Expand what is there, do not hallucinate new content areas.
2. Depth must match the course level. Apply the Academic Level Calibrator skill guidelines strictly.
3. Total estimated hours across all subtopics must be within 10% of the stated credit hours (1 credit = approximately 15 contact hours).
4. Prerequisites within the course must be logically ordered — a subtopic cannot list a prerequisite that appears after it in the syllabus.
5. If critic feedback is provided, address every identified gap specifically. Do not rewrite sections that were not flagged.

## Output Format
Return ONLY valid JSON matching this exact schema. No preamble, no explanation, no markdown code fences.

{
  "course_metadata": {
    "course_name": "string",
    "course_code": "string",
    "course_level": "UG" | "PG" | "PhD",
    "credit_hours": integer,
    "domain": "string",
    "institution": "string",
    "semester": "string",
    "prerequisites": ["string"]
  },
  "topics": [
    {
      "topic_name": "string",
      "unit_number": integer,
      "learning_intent": "string",
      "total_hours": float,
      "subtopics": [
        {
          "subtopic_name": "string",
          "depth_level": "introductory" | "intermediate" | "advanced",
          "estimated_hours": float,
          "description": "string",
          "prerequisites_within_course": ["string"]
        }
      ]
    }
  ],
  "total_hours": float,
  "coverage_summary": "string"
}
```

### prompts/gap_critic_prompt.md

```markdown
# Gap Critic System Prompt

You are a strict academic curriculum auditor. Your sole job is to identify gaps, errors, and problems in an expanded syllabus. You do not rewrite or improve — you only identify and report problems precisely.

## Your Inputs
You will receive:
- **Course metadata:** name, level, credit hours, prerequisites
- **Expanded syllabus draft:** the full syllabus produced by the Expander
- **Academic Level Calibrator skill:** guidelines for what is appropriate at this level

## Your Task
Evaluate the syllabus for the following gap types only:

### 1. missing_prerequisite
A subtopic requires knowledge that is not covered anywhere in this course or listed as a course prerequisite. Example: a subtopic on "Backpropagation" assumes knowledge of "Chain Rule of Calculus" which is neither in the syllabus nor in prerequisites.

### 2. coverage_gap
A topic that is clearly implied by the course name, domain, or explicitly listed in the raw curriculum is absent from the expansion. Example: a Data Structures course that has no coverage of Trees or Graphs.

### 3. sequencing_issue
Topics or subtopics are ordered in a way that a student cannot logically follow. Example: "Applying Dijkstra's Algorithm" appears before "Graph Representation" is introduced.

### 4. depth_mismatch
A subtopic's depth level or description does not match what is appropriate for the course level. Example: a PhD course subtopic described as "introductory overview" with 1 hour allocation for a foundational topic.

## Rules
1. Only report real problems. Do not invent gaps to seem thorough.
2. Be specific. Each gap must name the exact topic/subtopic and explain precisely what is wrong.
3. Each suggested_fix must be actionable — tell the Expander exactly what to do.
4. If you find no gaps, set has_gaps to false and gaps to empty array. Do not force-find problems.
5. Your confidence_score reflects how certain you are that the gaps you found are real (not false positives).

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown code fences.

{
  "has_gaps": boolean,
  "gaps": [
    {
      "gap_type": "missing_prerequisite" | "coverage_gap" | "sequencing_issue" | "depth_mismatch",
      "location": "string (topic name / subtopic name)",
      "description": "string (specific description of the problem)",
      "suggested_fix": "string (exact actionable instruction for the Expander)"
    }
  ],
  "overall_assessment": "string (one paragraph summary)",
  "confidence_score": float (0.0 to 1.0)
}
```

---

## Step 8 — Nodes

Each node is a function that receives the full Phase1State and returns a dict of only the fields it modifies.

### nodes/curriculum_loader.py

```python
# nodes/curriculum_loader.py

import json
from state import Phase1State, CourseMetadata
from dependencies import get_file_reader
from config import config
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def curriculum_loader_node(state: Phase1State) -> dict:
    """
    Node 1: Load and parse the curriculum file.
    
    Responsibilities:
    - Read curriculum file via file_reader interface
    - Use LLM to extract structured CourseMetadata from raw text
    - Set curriculum_raw and course_metadata in state
    
    Does NOT expand topics — that is the Expander's job.
    """

    file_reader = get_file_reader()

    # Read raw curriculum text
    curriculum_text = file_reader.read_curriculum(state.curriculum_file_path)

    # Use LLM to extract structured metadata from raw text
    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.0,    # deterministic for extraction tasks
        max_tokens=1024
    )

    extraction_prompt = f"""
Extract course metadata from this curriculum document. 
Return ONLY valid JSON with these exact fields, nothing else:

{{
  "course_name": "string",
  "course_code": "string",
  "course_level": "UG" or "PG" or "PhD",
  "credit_hours": integer,
  "domain": "string",
  "institution": "string",
  "semester": "string",
  "prerequisites": ["string"]
}}

Curriculum text:
{curriculum_text}
"""

    response = llm.invoke([HumanMessage(content=extraction_prompt)])

    try:
        metadata_dict = json.loads(response.content.strip())
        course_metadata = CourseMetadata(**metadata_dict)
    except (json.JSONDecodeError, ValueError) as e:
        # If extraction fails, create minimal metadata and continue
        # The expander will work with raw text
        print(f"[curriculum_loader] Metadata extraction failed: {e}. Using minimal metadata.")
        course_metadata = CourseMetadata(
            course_name="Unknown",
            course_code="UNKNOWN",
            course_level="UG",
            credit_hours=3,
            domain="Unknown",
            institution="Unknown",
            semester="Unknown",
            prerequisites=[]
        )

    return {
        "curriculum_raw": curriculum_text,
        "course_metadata": course_metadata
    }
```

### nodes/skill_injector.py

```python
# nodes/skill_injector.py

from state import Phase1State
from dependencies import get_skill_loader


def skill_injector_node(state: Phase1State) -> dict:
    """
    Node 2: Load and inject skill MD files into state.
    
    Reads skill files via skill_loader interface and stores their
    content in state fields. These fields are then used by the
    Expander and Critic nodes as part of their prompt context.
    
    Runs once at graph entry. Skills do not change across iterations.
    """

    skill_loader = get_skill_loader()

    level_calibrator = skill_loader.load("academic_level_calibrator.md")
    parser_instructions = skill_loader.load("curriculum_parser_instructions.md")

    print(f"[skill_injector] Loaded {len(skill_loader.list_available_skills())} skills")

    return {
        "level_calibrator_skill": level_calibrator,
        "parser_instructions_skill": parser_instructions
    }
```

### nodes/expander.py

```python
# nodes/expander.py

import os
import json
from state import Phase1State, SyllabusDraft
from dependencies import get_tool_runner
from config import config
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def _load_prompt(prompt_file: str) -> str:
    prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_expander_context(state: Phase1State) -> str:
    """Build the full user message context for the expander."""

    context_parts = []

    # Course metadata
    if state.course_metadata:
        context_parts.append(f"""
## Course Metadata
- Name: {state.course_metadata.course_name}
- Code: {state.course_metadata.course_code}
- Level: {state.course_metadata.course_level}
- Credit Hours: {state.course_metadata.credit_hours}
- Domain: {state.course_metadata.domain}
- Institution: {state.course_metadata.institution}
- Semester: {state.course_metadata.semester}
- Prerequisites: {', '.join(state.course_metadata.prerequisites) or 'None'}
""")

    # Academic level calibrator skill
    context_parts.append(f"""
## Academic Level Calibrator Skill
{state.level_calibrator_skill}
""")

    # Raw curriculum
    context_parts.append(f"""
## Raw Curriculum
{state.curriculum_raw}
""")

    # Critic feedback (only if this is a refinement iteration)
    if state.critic_feedback and state.critic_feedback.has_gaps and state.iteration_count > 0:
        gaps_text = "\n".join([
            f"- [{g.gap_type}] At '{g.location}': {g.description}. Fix: {g.suggested_fix}"
            for g in state.critic_feedback.gaps
        ])
        context_parts.append(f"""
## Critic Feedback from Previous Iteration (Address These Specifically)
{state.critic_feedback.overall_assessment}

Specific gaps to fix:
{gaps_text}
""")

    # Similar topics from other courses (if tool returned results)
    if state.similar_topics_found:
        overlap_text = "\n".join([
            f"- '{r['topic']}' is covered in {r['course_name']} ({r['course_code']}) at {r['coverage_level']} level"
            for r in state.similar_topics_found
        ])
        context_parts.append(f"""
## Topics Already Covered in Prerequisite Courses (Avoid Duplication)
{overlap_text}
""")

    return "\n".join(context_parts)


def expander_node(state: Phase1State) -> dict:
    """
    Node 3: Expand the curriculum into a detailed structured syllabus.
    
    Uses the full curriculum text, course metadata, skill context, and
    critic feedback (if refinement iteration) to produce a SyllabusDraft.
    
    Also invokes the similarity search tool if needed to check for
    topic overlap with prerequisite courses.
    """

    # Optionally invoke similarity search tool
    # In mock mode this returns empty — handled gracefully
    tool_runner = get_tool_runner()
    similar_topics = []

    if state.course_metadata and state.course_metadata.prerequisites:
        # Extract topic names from curriculum for similarity check
        # Simple extraction — just use key words from the raw curriculum
        curriculum_words = state.curriculum_raw[:500]  # first 500 chars as a rough topic signal
        try:
            similar_topics = tool_runner.run_similarity_search(
                topics=[curriculum_words],
                top_k=5
            )
        except Exception as e:
            print(f"[expander] Similarity search failed (non-fatal): {e}")
            similar_topics = []

    # Build prompt context
    system_prompt = _load_prompt("expander_prompt.md")
    user_context = _build_expander_context(
        Phase1State(**{**state.model_dump(), "similar_topics_found": similar_topics})
    )

    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_context)
    ])

    # Parse structured output
    raw_output = response.content.strip()

    # Strip markdown code fences if model adds them despite instructions
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]

    try:
        syllabus_dict = json.loads(raw_output)
        syllabus_draft = SyllabusDraft(**syllabus_dict)
    except (json.JSONDecodeError, ValueError) as e:
        # On parse failure, do not crash — return the current draft unchanged
        # The critic will identify this as a gap in the next iteration
        print(f"[expander] Failed to parse LLM output: {e}")
        return {
            "similar_topics_found": similar_topics
        }

    print(f"[expander] Iteration {state.iteration_count + 1}: Produced {len(syllabus_draft.topics)} units")

    return {
        "syllabus_draft": syllabus_draft,
        "similar_topics_found": similar_topics
    }
```

### nodes/gap_critic.py

```python
# nodes/gap_critic.py

import os
import json
from state import Phase1State, CriticFeedback, CriticGap
from config import config
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def _load_prompt(prompt_file: str) -> str:
    prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_critic_context(state: Phase1State) -> str:
    """Build the user message context for the gap critic."""

    syllabus_json = json.dumps(
        state.syllabus_draft.model_dump(),
        indent=2
    ) if state.syllabus_draft else "No syllabus draft available."

    metadata_text = ""
    if state.course_metadata:
        metadata_text = f"""
## Course Metadata
- Name: {state.course_metadata.course_name}
- Level: {state.course_metadata.course_level}
- Credit Hours: {state.course_metadata.credit_hours}
- Domain: {state.course_metadata.domain}
- Prerequisites: {', '.join(state.course_metadata.prerequisites) or 'None'}
"""

    return f"""
{metadata_text}

## Academic Level Calibrator Skill
{state.level_calibrator_skill}

## Syllabus Draft to Evaluate
{syllabus_json}
"""


def gap_critic_node(state: Phase1State) -> dict:
    """
    Node 4: Evaluate the expanded syllabus for gaps.
    
    Evaluates specifically for:
    - missing_prerequisite: knowledge assumed but not covered
    - coverage_gap: topics implied by course but absent
    - sequencing_issue: illogical topic ordering
    - depth_mismatch: depth inappropriate for course level
    
    Does NOT rewrite or improve — only identifies and reports.
    Returns CriticFeedback with has_gaps flag and specific gap list.
    """

    if not state.syllabus_draft:
        # If no draft exists (expander failed), report a gap
        return {
            "critic_feedback": CriticFeedback(
                has_gaps=True,
                gaps=[CriticGap(
                    gap_type="coverage_gap",
                    location="entire syllabus",
                    description="No syllabus draft was produced by the expander.",
                    suggested_fix="Generate a complete syllabus expansion."
                )],
                overall_assessment="Expander failed to produce a syllabus.",
                confidence_score=1.0
            )
        }

    system_prompt = _load_prompt("gap_critic_prompt.md")
    user_context = _build_critic_context(state)

    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.1,    # low temperature for evaluation tasks
        max_tokens=2048
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_context)
    ])

    raw_output = response.content.strip()

    # Strip markdown fences
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]

    try:
        feedback_dict = json.loads(raw_output)
        gaps = [CriticGap(**g) for g in feedback_dict.get("gaps", [])]
        critic_feedback = CriticFeedback(
            has_gaps=feedback_dict.get("has_gaps", False),
            gaps=gaps,
            overall_assessment=feedback_dict.get("overall_assessment", ""),
            confidence_score=feedback_dict.get("confidence_score", 0.5)
        )
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[gap_critic] Failed to parse critic output: {e}")
        # On parse failure, assume no gaps to avoid infinite loops
        critic_feedback = CriticFeedback(
            has_gaps=False,
            gaps=[],
            overall_assessment="Critic output could not be parsed. Passing through.",
            confidence_score=0.0
        )

    gap_count = len(critic_feedback.gaps)
    print(f"[gap_critic] Iteration {state.iteration_count + 1}: Found {gap_count} gaps. has_gaps={critic_feedback.has_gaps}")

    return {"critic_feedback": critic_feedback}
```

### nodes/output_writer.py

```python
# nodes/output_writer.py

from state import Phase1State
from dependencies import get_db_writer


def output_writer_node(state: Phase1State) -> dict:
    """
    Node 5: Write the final syllabus to persistent storage.
    
    Determines phase_status based on how the graph exited:
    - "passed": critic found no gaps
    - "force_passed": max iterations reached, passing despite remaining gaps
    
    Calls db_writer interface to persist the output.
    """

    db_writer = get_db_writer()

    if not state.syllabus_draft:
        return {
            "phase_status": "failed",
            "phase_error": "No syllabus draft available to write."
        }

    # Determine status
    if state.critic_feedback and not state.critic_feedback.has_gaps:
        phase_status = "passed"
    else:
        phase_status = "force_passed"

    course_code = state.course_metadata.course_code if state.course_metadata else "UNKNOWN"

    try:
        record_id = db_writer.write_syllabus(
            syllabus=state.syllabus_draft,
            course_code=course_code,
            phase_status=phase_status,
            iteration_count=state.iteration_count
        )
        print(f"[output_writer] Syllabus written. Record ID: {record_id}. Status: {phase_status}")
    except Exception as e:
        return {
            "phase_status": "failed",
            "phase_error": str(e)
        }

    return {
        "syllabus_final": state.syllabus_draft,
        "phase_status": phase_status
    }
```

---

## Step 9 — Graph Assembly

```python
# graph.py

from langgraph.graph import StateGraph, END
from state import Phase1State
from nodes.curriculum_loader import curriculum_loader_node
from nodes.skill_injector import skill_injector_node
from nodes.expander import expander_node
from nodes.gap_critic import gap_critic_node
from nodes.output_writer import output_writer_node
from config import config


def router(state: Phase1State) -> str:
    """
    Conditional edge function. Called after gap_critic_node.
    
    Routing logic:
    - If no gaps found → go to output_writer
    - If gaps found AND iterations remaining → go back to expander
    - If gaps found AND max iterations reached → go to output_writer (force_pass)
    
    Returns the name of the next node.
    """

    # Increment iteration count
    # Note: state is immutable here — we return a new iteration count
    # but LangGraph does not update state inside a router.
    # Iteration tracking is done via the state passed to nodes.

    if not state.critic_feedback:
        # No feedback yet — should not happen, but route forward
        return "output_writer"

    if not state.critic_feedback.has_gaps:
        print(f"[router] No gaps found. Routing to output_writer.")
        return "output_writer"

    if state.iteration_count >= state.iteration_max:
        print(f"[router] Max iterations ({state.iteration_max}) reached. Force-passing to output_writer.")
        return "output_writer"

    print(f"[router] Gaps found ({len(state.critic_feedback.gaps)}). Routing back to expander. Iteration {state.iteration_count + 1}/{state.iteration_max}")
    return "expander"


def increment_iteration(state: Phase1State) -> dict:
    """
    A lightweight node that increments the iteration counter.
    Placed between gap_critic and expander on the refinement path
    so that iteration_count is accurate when expander receives state.
    """
    return {"iteration_count": state.iteration_count + 1}


def build_phase1_graph() -> StateGraph:
    """
    Assemble and compile the Phase 1 LangGraph graph.
    
    Graph structure:
    curriculum_loader → skill_injector → expander → gap_critic → router
                                            ↑                       |
                                    iteration_counter ←── (gaps found)
                                                                    |
                                                           (no gaps or max iter)
                                                                    ↓
                                                            output_writer → END
    """

    graph = StateGraph(Phase1State)

    # Register nodes
    graph.add_node("curriculum_loader", curriculum_loader_node)
    graph.add_node("skill_injector", skill_injector_node)
    graph.add_node("expander", expander_node)
    graph.add_node("gap_critic", gap_critic_node)
    graph.add_node("iteration_counter", increment_iteration)
    graph.add_node("output_writer", output_writer_node)

    # Linear entry sequence
    graph.set_entry_point("curriculum_loader")
    graph.add_edge("curriculum_loader", "skill_injector")
    graph.add_edge("skill_injector", "expander")
    graph.add_edge("expander", "gap_critic")

    # Conditional routing after critic
    graph.add_conditional_edges(
        "gap_critic",
        router,
        {
            "expander": "iteration_counter",    # gaps found → increment then re-expand
            "output_writer": "output_writer"    # no gaps or force-pass → write output
        }
    )

    # Iteration counter feeds back to expander
    graph.add_edge("iteration_counter", "expander")

    # Output writer is the terminal node
    graph.add_edge("output_writer", END)

    return graph.compile()


# Compiled graph — import this in your runner script
phase1_graph = build_phase1_graph()
```

---

## Step 10 — Test Data

### test_data/sample_curriculum.md

Create a real curriculum document here. Use an actual course from your institution. The richer this file is, the better you can validate expander and critic behavior. Minimum viable test curriculum:

```markdown
# Course: Data Structures and Algorithms
**Code:** CSE2001  
**Level:** UG (Second Year)  
**Credits:** 4  
**Prerequisites:** Programming Fundamentals, Discrete Mathematics  

## Unit 1: Arrays and Linked Lists
- Array representation and operations
- Singly and doubly linked lists
- Circular linked lists
- Applications

## Unit 2: Stacks and Queues
- Stack ADT and implementations
- Queue ADT and implementations
- Deque
- Applications: expression evaluation, BFS

## Unit 3: Trees
- Binary trees
- Binary search trees
- AVL trees
- Heap and priority queues

## Unit 4: Graphs
- Graph representations
- BFS and DFS
- Shortest path algorithms
- Minimum spanning trees

## Unit 5: Sorting and Searching
- Comparison-based sorting algorithms
- Linear time sorting
- Binary search and variants
- Hashing
```

---

## Step 11 — Running the Graph

```python
# run_phase1.py

from graph import phase1_graph
from state import Phase1State
from config import config


def run_phase1(curriculum_file_path: str) -> Phase1State:
    """
    Run Phase 1 for a single curriculum file.
    
    Args:
        curriculum_file_path: Path to the curriculum MD or PDF file
    
    Returns:
        Final Phase1State with syllabus_final and phase_status set
    """

    initial_state = Phase1State(
        curriculum_file_path=curriculum_file_path,
        iteration_max=config.MAX_ITERATIONS
    )

    print(f"\n{'='*60}")
    print(f"Phase 1 Starting: {curriculum_file_path}")
    print(f"Max iterations: {config.MAX_ITERATIONS}")
    print(f"Dependency mode: {config.DEPENDENCY_MODE}")
    print(f"{'='*60}\n")

    final_state = phase1_graph.invoke(initial_state)

    print(f"\n{'='*60}")
    print(f"Phase 1 Complete")
    print(f"Status: {final_state['phase_status']}")
    print(f"Iterations used: {final_state['iteration_count']}")
    if final_state.get('syllabus_final'):
        print(f"Units generated: {len(final_state['syllabus_final']['topics'])}")
    print(f"{'='*60}\n")

    return final_state


if __name__ == "__main__":
    result = run_phase1("sample_curriculum.md")
```

---

## Step 12 — Tests

### tests/test_state.py

```python
# tests/test_state.py

import pytest
from state import Phase1State, CourseMetadata, SyllabusDraft, CriticFeedback


def test_phase1_state_defaults():
    state = Phase1State()
    assert state.iteration_count == 0
    assert state.iteration_max == 3
    assert state.phase_status == ""
    assert state.syllabus_draft is None
    assert state.critic_feedback is None


def test_phase1_state_with_metadata():
    metadata = CourseMetadata(
        course_name="Data Structures",
        course_code="CSE2001",
        course_level="UG",
        credit_hours=4,
        domain="Computer Science",
        institution="UPES",
        semester="Semester 3"
    )
    state = Phase1State(course_metadata=metadata)
    assert state.course_metadata.course_code == "CSE2001"
    assert state.course_metadata.course_level == "UG"
```

### tests/test_nodes.py

```python
# tests/test_nodes.py

import pytest
import os
from unittest.mock import patch
from state import Phase1State, CourseMetadata
from nodes.skill_injector import skill_injector_node


def test_skill_injector_loads_skills():
    """Skill injector must load both required skills."""
    state = Phase1State()
    
    # Only run if skill files exist
    skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")
    if not os.path.exists(skills_dir):
        pytest.skip("Skills directory not yet created")
    
    result = skill_injector_node(state)
    
    assert "level_calibrator_skill" in result
    assert "parser_instructions_skill" in result
    assert len(result["level_calibrator_skill"]) > 0
    assert len(result["parser_instructions_skill"]) > 0


def test_curriculum_loader_raises_on_missing_file():
    """Curriculum loader must raise FileNotFoundError for missing files."""
    from nodes.curriculum_loader import curriculum_loader_node
    
    state = Phase1State(curriculum_file_path="nonexistent_file.md")
    
    with pytest.raises(FileNotFoundError):
        curriculum_loader_node(state)
```

### tests/test_graph.py

```python
# tests/test_graph.py

import pytest
import os
from graph import phase1_graph
from state import Phase1State
from config import config


@pytest.mark.skipif(
    not os.path.exists(os.path.join(config.TEST_DATA_DIR, "sample_curriculum.md")),
    reason="sample_curriculum.md not found in test_data/"
)
def test_phase1_graph_end_to_end():
    """
    Full end-to-end graph run using mock dependencies and sample curriculum.
    Validates that the graph completes without error and produces a valid output.
    """

    initial_state = Phase1State(
        curriculum_file_path="sample_curriculum.md",
        iteration_max=2   # use 2 for faster tests
    )

    result = phase1_graph.invoke(initial_state)

    assert result["phase_status"] in ["passed", "force_passed"]
    assert result["syllabus_final"] is not None
    assert len(result["syllabus_final"]["topics"]) > 0
    assert result["iteration_count"] >= 1
```

---

## Integration Checklist — When MCP and DB Are Ready

When your team member delivers the MCP servers and DB, follow this exact swap process. **Do not modify any node or graph code.**

- [ ] Implement `MCPFileReader` matching `interfaces/file_reader.py` exactly
- [ ] Implement `MCPPostgresWriter` matching `interfaces/db_writer.py` exactly
- [ ] Implement `MCPSkillLoader` matching `interfaces/skill_loader.py` exactly
- [ ] Implement `MCPToolRunner` matching `interfaces/tool_runner.py` exactly
- [ ] Place all four implementations in a new `implementations/` directory
- [ ] In `dependencies.py`, update each `get_*()` function to return the real implementation when `DEPENDENCY_MODE == "real"`
- [ ] Set `DEPENDENCY_MODE=real` in `.env`
- [ ] Run `tests/test_graph.py` — all tests must pass unchanged

---

## Environment File Template

Create a `.env` file at the root of `phase1/`:

```
LLM_BASE_URL=http://192.168.1.13:8000/v1
LLM_API_KEY=dummy
LLM_MODEL_NAME=meta-llama/Llama-3.1-70B-Instruct
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4096
MAX_ITERATIONS=3
DEPENDENCY_MODE=mock
```

---

## What the Coding Agent Must Not Do

- Do not hardcode any file paths, model names, or API keys inside nodes
- Do not import from `mocks/` directly inside nodes — always go through `dependencies.py`
- Do not add new state fields without updating `state.py` first and documenting the field
- Do not catch all exceptions silently — log them with the node name prefix e.g. `[expander]`
- Do not run the LLM inside `graph.py` — all LLM calls belong inside nodes
- Do not modify the router logic to add more destination nodes without updating this document
