from abc import ABC, abstractmethod
from phase1.state import SyllabusDraft

class DBWriter(ABC):
    @abstractmethod
    def write_syllabus(self, syllabus: SyllabusDraft, course_code: str, phase_status: str, iteration_count: int) -> str: pass
    @abstractmethod
    def check_syllabus_exists(self, course_code: str) -> bool: pass
