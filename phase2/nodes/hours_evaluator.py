import os
import json
from phase2.state import Phase2State
from phase2.config import config
from phase2.logger import log_llm_response
from phase2.dependencies import get_custom_tools
from phase2.utils import parse_evaluation
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def _load_prompt(filename: str) -> str:
    path = os.path.join(config.PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def hours_evaluator_node(state: Phase2State) -> dict:
    print("[hours_evaluator] Starting credit hour allocation check...")

    syllabus = state.syllabus_draft
    meta = syllabus.course_metadata

    # Collect all subtopic hours across all units
    all_subtopic_hours = [
        st.estimated_hours
        for topic in syllabus.topics
        for st in topic.subtopics
    ]

    # Call the deterministic Custom Tools calculator (no LLM involved here)
    custom_tools = get_custom_tools()
    calc_result = custom_tools.calculate_credit_hours(all_subtopic_hours, meta.credit_hours)

    context = f"""## Course Metadata
- Name: {meta.course_name}
- Level: {meta.course_level}
- Credit Hours: {meta.credit_hours}

## Credit Hour Calculator Result
- Total subtopic hours: {calc_result['total_hours']:.1f}
- Expected lecture hours (credit_hours × 15): {calc_result['expected_hours']}
- Delta: {calc_result['delta']:+.1f} hours
- Within ±10% tolerance: {calc_result['within_tolerance']}
- Tolerance threshold: ±{calc_result['tolerance_threshold']:.1f} hours

## Full Syllabus (for distribution analysis)
{json.dumps(syllabus.model_dump(), indent=2)}
"""

    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
    )

    system_prompt = _load_prompt("hours_evaluator_prompt.md")
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ])
    log_llm_response("hours_evaluator", response.content)

    result = parse_evaluation(response.content, "hours_evaluator")

    # Hard override: if calculator says total is out of tolerance, force fail regardless of LLM
    if not calc_result["within_tolerance"] and result.passed:
        delta_str = f"{calc_result['delta']:+.1f}"
        result.passed = False
        result.feedback = (
            f"[Auto-fail] Total estimated hours ({calc_result['total_hours']:.1f}) "
            f"is {delta_str} hours from the expected {calc_result['expected_hours']} hours, "
            f"which exceeds the ±{calc_result['tolerance_threshold']:.1f}h tolerance. "
            + result.feedback
        )

    print(f"[hours_evaluator] passed={result.passed} | confidence={result.confidence_score:.2f}")
    return {"hours_evaluation": result}
