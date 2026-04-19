from abc import ABC, abstractmethod

class SkillLoader(ABC):
    @abstractmethod
    def load(self, skill_name: str) -> str: pass
