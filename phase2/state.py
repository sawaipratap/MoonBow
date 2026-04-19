from typing import Optional
from pydantic import BaseModel
from phase1.state import SyllabusDraft

class EvaluationResult(BaseModel):
    passed: bool
    feedback: str
    confidence_score: float = 1.0

class Phase2State(BaseModel):
    # Input field - parsed from Phase 1 output
    syllabus_draft: Optional[SyllabusDraft] = None

    # Injected context - set by skill_injector node
    level_calibrator_skill: str = ""

    # Phase Evaluator Nodes Output variables (Parallel)
    level_evaluation: Optional[EvaluationResult] = None
    sequence_evaluation: Optional[EvaluationResult] = None
    hours_evaluation: Optional[EvaluationResult] = None
    relevance_evaluation: Optional[EvaluationResult] = None

    # Output fields (Set by Aggregator)
    aggregated_feedback: str = ""
    # "passed", "failed_needs_phase1_rework", "failed_unexpectedly", ""
    phase_status: str = ""  

    class Config:
        arbitrary_types_allowed = True
