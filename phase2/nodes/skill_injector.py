from phase2.state import Phase2State
from phase2.dependencies import get_skill_loader


def skill_injector_node(state: Phase2State) -> dict:
    skill_loader = get_skill_loader()
    level_calibrator = skill_loader.load("academic_level_calibrator.md")
    print(f"[skill_injector] Loaded academic_level_calibrator.md ({len(level_calibrator)} chars)")
    return {"level_calibrator_skill": level_calibrator}
