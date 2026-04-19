import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM settings — shared with phase1, reads same env vars
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.minimax.io/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "MiniMax-M2.7")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))  # lower for evaluation
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # Paths
    PROMPTS_DIR: str = os.path.join(os.path.dirname(__file__), "prompts")
    TEAM_SKILLS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills", "knowledge")

    # Phase 2 tuning
    # Minimum score for an evaluator to pass (0.0–1.0)
    EVALUATOR_PASS_THRESHOLD: float = float(os.getenv("EVALUATOR_PASS_THRESHOLD", "0.70"))

config = Config()
