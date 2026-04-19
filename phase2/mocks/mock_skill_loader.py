import os
from phase2.interfaces.skill_loader import SkillLoader
from phase2.config import config


class MockSkillLoader(SkillLoader):
    """Reads skill MD files directly from the local skills/knowledge/ directory."""

    def load(self, skill_name: str) -> str:
        path = os.path.join(config.TEAM_SKILLS_DIR, skill_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"MockSkillLoader: Skill not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
