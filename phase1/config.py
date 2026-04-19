import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM settings
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.minimax.io/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "sk-cp-AKOOWaYRVYU_U1diTn22tSM4Jd1IjpuMsXnzIpeLTbLQA2F1x3_lbfqJMPSlhb5zu2DVGjzuxJVAauzfOVZZLMTvTpJ9PJE5tt9KDTvr7-QKwZhuCCR3EIo")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "MiniMax-M2.7")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "190000"))

    # Graph settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))

    PROMPTS_DIR: str = os.path.join(os.path.dirname(__file__), "prompts")

    TEAM_SKILLS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills", "knowledge")

config = Config()
