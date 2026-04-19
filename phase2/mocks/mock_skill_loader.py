import os
import glob
import json
from phase2.interfaces.skill_loader import SkillLoader
from phase2.config import config

class MockSkillLoader(SkillLoader):
    """
    Loads skill files from the local skills/knowledge directory.
    Mirrors Phase 1 MockSkillLoader behavior exactly.
    """

    def load(self, skill_name: str) -> str:
        skill_path = os.path.join(config.TEAM_SKILLS_DIR, skill_name)
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"[skill_loader] Loaded skill: {skill_name}")
            return content
        print(f"[skill_loader] Warning: skill file not found: {skill_path}. Using empty stub.")
        return f"[Skill '{skill_name}' not yet available — using empty stub for development]"

    def list_available_skills(self) -> list[str]:
        pattern = os.path.join(config.TEAM_SKILLS_DIR, "*.md")
        return [os.path.basename(p) for p in glob.glob(pattern)]
