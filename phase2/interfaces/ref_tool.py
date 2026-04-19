from abc import ABC, abstractmethod

class RefTool(ABC):
    @abstractmethod
    def lookup_benchmark_curriculum(self, domain: str, level: str, top_k: int = 3) -> dict: pass

    @abstractmethod
    def lookup_accreditation_standards(self, domain: str, level: str, accreditation_body: str = "NBA") -> dict: pass
