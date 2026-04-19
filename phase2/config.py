import os
from dotenv import load_dotenv

load_dotenv()

class Phase2Config:
    # Shared LLM settings (same server as Phase 1)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.minimax.io/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "sk-cp-AKOOWaYRVYU_U1diTn22tSM4Jd1IjpuMsXnzIpeLTbLQA2F1x3_lbfqJMPSlhb5zu2DVGjzuxJVAauzfOVZZLMTvTpJ9PJE5tt9KDTvr7-QKwZhuCCR3EIo")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "MiniMax-M2.7")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "190000"))

    # Phase 2 specific
    PROMPTS_DIR: str = os.path.join(os.path.dirname(__file__), "prompts")
    DEPENDENCY_MODE: str = os.getenv("DEPENDENCY_MODE", "mock")

    # Phase 1 mock output dir — Phase 2 reads syllabus from here in mock mode
    PHASE1_MOCK_OUTPUT_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "phase1", "mock_outputs"
    )

    # Phase 2 mock output
    MOCK_OUTPUT_DIR: str = os.path.join(os.path.dirname(__file__), "mock_outputs")

    # Reference to team skills directory
    TEAM_SKILLS_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "skills", "knowledge"
    )

    # Hours tolerance — how much % over/under credit hours is acceptable
    HOURS_TOLERANCE_PERCENT: float = float(os.getenv("HOURS_TOLERANCE_PERCENT", "10.0"))

config = Phase2Config()
