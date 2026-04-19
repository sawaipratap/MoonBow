from abc import ABC, abstractmethod
from phase1.state import SyllabusDraft

class DBReader(ABC):
    @abstractmethod
    def read_syllabus(self, course_code: str) -> dict: pass
