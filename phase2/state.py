from typing import Optional
from pydantic import BaseModel

# Reuse Phase 1 data models — Phase 2 works on the same SyllabusDraft structure
from phase1.state import SyllabusDraft, CourseMetadata


class EvaluatorResult(BaseModel):
    evaluator: str          # "level" | "sequence" | "hours" | "relevance"
    passed: bool
    score: float            # 0.0–1.0
    feedback: str           # specific, actionable description of what failed
    status: str             # "passed" | "failed" | "skipped"


class Phase2State(BaseModel):
    # Input — set at graph entry
    course_code: str = ""
    syllabus_draft: Optional[SyllabusDraft] = None
    phase1_status: str = ""             # "passed" | "force_passed" from Phase 1

    # Injected skill — set by skill_injector node
    level_calibrator_skill: str = ""

    # Evaluator outputs — set in parallel by the 4 evaluator nodes
    level_eval_result: Optional[EvaluatorResult] = None
    sequence_eval_result: Optional[EvaluatorResult] = None
    hours_eval_result: Optional[EvaluatorResult] = None
    relevance_eval_result: Optional[EvaluatorResult] = None

    # Output — set by aggregator and output_writer
    phase_status: str = ""              # "passed" | "failed" | "returned_to_phase1"
    phase_error: str = ""
    compiled_feedback: str = ""         # sent back to Phase 1 expander if any evaluator fails

    class Config:
        arbitrary_types_allowed = True
