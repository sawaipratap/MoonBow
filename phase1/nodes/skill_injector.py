from phase1.state import Phase1State
from phase1.dependencies import get_skill_loader

def skill_injector_node(state: Phase1State) -> dict:
    skill_loader = get_skill_loader()
    level_calibrator = skill_loader.load("academic_level_calibrator.md")
    parser_instructions = skill_loader.load("curriculum_parser_instructions.md")

    print(f"[skill_injector] Loaded skills via MCP.")

    return {
        "level_calibrator_skill": level_calibrator,
        "parser_instructions_skill": parser_instructions
    }
