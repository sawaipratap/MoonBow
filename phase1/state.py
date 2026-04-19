from typing import Optional
from pydantic import BaseModel

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
