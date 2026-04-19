import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from phase2.state import Phase2State, EvaluatorResult
from phase2.config import config
from phase2.logger import log_llm_response
from phase2.nodes.level_evaluator import _parse_evaluator_response
import os


def _load_prompt() -> str:
    path = os.path.join(config.PROMPTS_DIR, "hours_evaluator_prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def hours_evaluator_node(state: Phase2State) -> dict:
    syllabus = state.syllabus_draft
    credit_hours = syllabus.course_metadata.credit_hours
    total_hours = syllabus.total_hours

    # Credit hours → contact hours conversion rule (standard: 1 credit = 15 contact hours)
    expected_hours = credit_hours * 15
    tolerance = 0.10   # ±10%
    lower = expected_hours * (1 - tolerance)
    upper = expected_hours * (1 + tolerance)
    within_range = lower <= total_hours <= upper
    deviation_pct = abs(total_hours - expected_hours) / expected_hours * 100

    # Build hour distribution stats per unit
    unit_hours = [
        {"unit": t.topic_name, "hours": t.total_hours, "pct": round(t.total_hours / total_hours * 100, 1)}
        for t in syllabus.topics
    ]
    max_unit_pct = max(u["pct"] for u in unit_hours) if unit_hours else 0

    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.0,
        max_tokens=config.LLM_MAX_TOKENS
    )

    prompt_template = _load_prompt()
    prompt = prompt_template.format(
        credit_hours=credit_hours,
        expected_hours=expected_hours,
        total_hours=total_hours,
        deviation_pct=round(deviation_pct, 1),
        within_range=within_range,
        unit_hours_json=json.dumps(unit_hours, indent=2),
        max_unit_pct=max_unit_pct,
        syllabus_json=json.dumps(syllabus.model_dump(), indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    log_llm_response("hours_evaluator", response.content)

    result = _parse_evaluator_response(response.content, "hours")
    print(f"[hours_evaluator] {total_hours}h vs expected {expected_hours}h "
          f"({deviation_pct:.1f}% deviation) — {'PASS' if result.passed else 'FAIL'}")
    return {"hours_eval_result": result}
