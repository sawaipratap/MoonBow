import os
import json
from phase2.state import Phase2State
from phase2.config import config
from phase2.logger import log_llm_response
from phase2.dependencies import get_reference_db
from phase2.utils import parse_evaluation
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def _load_prompt(filename: str) -> str:
    path = os.path.join(config.PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def relevance_evaluator_node(state: Phase2State) -> dict:
    print("[relevance_evaluator] Starting industry/accreditation relevance check...")

    syllabus = state.syllabus_draft
    meta = syllabus.course_metadata

    # Fetch benchmark reference for this domain and level
    ref_db = get_reference_db()
    benchmark = ref_db.lookup(meta.domain, meta.course_level)

    context = f"""## Course Metadata
- Name: {meta.course_name}
- Code: {meta.course_code}
- Level: {meta.course_level}
- Domain: {meta.domain}

## Benchmark Reference (from Reference Database)
{benchmark}

## Syllabus to Evaluate
{json.dumps(syllabus.model_dump(), indent=2)}
"""

    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )

    system_prompt = _load_prompt("relevance_evaluator_prompt.md")
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ])
    log_llm_response("relevance_evaluator", response.content)

    result = parse_evaluation(response.content, "relevance_evaluator")
    print(f"[relevance_evaluator] passed={result.passed} | confidence={result.confidence_score:.2f}")
    return {"relevance_evaluation": result}
