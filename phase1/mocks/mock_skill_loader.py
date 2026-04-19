import os
from phase1.interfaces.skill_loader import SkillLoader
from phase1.config import config

class MockSkillLoader(SkillLoader):
    """
    Reads directly from your team's /skills/knowledge folder
    instead of using the mock skills.
    """
    def load(self, skill_name: str) -> str:
        skill_path = os.path.join(config.TEAM_SKILLS_DIR, skill_name)
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_available_skills(self) -> list[str]:
        if not os.path.exists(config.TEAM_SKILLS_DIR): return []
        return [f for f in os.listdir(config.TEAM_SKILLS_DIR) if f.endswith(".md")]
