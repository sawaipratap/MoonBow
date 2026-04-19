from abc import ABC, abstractmethod
from phase1.state import SyllabusDraft

class DBReader(ABC):
    """Reads the Phase 1 syllabus from the database (PostgreSQL MCP in production, mock JSON in dev)."""

    @abstractmethod
    def read_latest_syllabus(self, course_code: str) -> SyllabusDraft: pass

class DBWriter(ABC):
    """Writes Phase 2's refined syllabus result back to the database."""

    @abstractmethod
    def write_refined_syllabus(
        self,
        syllabus: SyllabusDraft,
        course_code: str,
        phase_status: str,
        evaluator_results: dict
    ) -> str: pass
