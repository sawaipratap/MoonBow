from abc import ABC, abstractmethod
from phase1.state import SyllabusDraft

class DBWriter(ABC):
    @abstractmethod
    def write_refined_syllabus(self, syllabus: SyllabusDraft, course_code: str, evaluation_results: dict) -> str: pass
