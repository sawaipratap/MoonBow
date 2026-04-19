from abc import ABC, abstractmethod

class SkillLoader(ABC):
    @abstractmethod
    def load(self, skill_name: str) -> str: pass
    @abstractmethod
    def list_available_skills(self) -> list[str]: pass
