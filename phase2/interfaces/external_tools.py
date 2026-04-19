from abc import ABC, abstractmethod

class ReferenceDB(ABC):
    """Interface to the Reference Database MCP (accreditation standards, benchmark curricula)."""

    @abstractmethod
    def lookup(self, domain: str, level: str) -> str:
        """
        Returns a text block describing benchmark curricula and accreditation standards
        for a given domain (e.g. 'Computer Science') and level (e.g. 'UG').
        """
        pass

class CustomToolsRunner(ABC):
    """Interface to the Custom Tools MCP (credit hour calculator, etc.)."""

    @abstractmethod
    def calculate_credit_hours(self, subtopic_hours: list[float], stated_credit_hours: int) -> dict:
        """
        Takes the list of all subtopic estimated_hours and the course's stated credit hours.
        Returns a dict:
          {
            "total_hours": float,
            "expected_hours": float,
            "delta": float,
            "within_tolerance": bool
          }
        """
        pass
