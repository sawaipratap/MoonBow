import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from phase2.state import Phase2State, EvaluatorResult
from phase2.config import config
from phase2.logger import log_llm_response
import os


def _load_prompt() -> str:
    path = os.path.join(config.PROMPTS_DIR, "level_evaluator_prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def level_evaluator_node(state: Phase2State) -> dict:
    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.0,   # deterministic — evaluation must be reproducible
        max_tokens=config.LLM_MAX_TOKENS
    )

    prompt_template = _load_prompt()
    syllabus_json = json.dumps(state.syllabus_draft.model_dump(), indent=2)

    prompt = prompt_template.format(
        level_calibrator_skill=state.level_calibrator_skill,
        course_level=state.syllabus_draft.course_metadata.course_level,
        syllabus_json=syllabus_json
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    log_llm_response("level_evaluator", response.content)

    result = _parse_evaluator_response(response.content, "level")
    print(f"[level_evaluator] Result: {'PASS' if result.passed else 'FAIL'} "
          f"(score={result.score:.2f})")
    return {"level_eval_result": result}


def _parse_evaluator_response(raw: str, evaluator_name: str) -> EvaluatorResult:
    """Extract JSON from LLM response and parse into EvaluatorResult."""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in response")
        data = json.loads(raw[start:end])
        score = float(data.get("score", 0.0))
        passed = data.get("pass", score >= config.EVALUATOR_PASS_THRESHOLD)
        return EvaluatorResult(
            evaluator=evaluator_name,
            passed=passed,
            score=score,
            feedback=data.get("feedback", ""),
            status="passed" if passed else "failed"
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"[{evaluator_name}_evaluator] Failed to parse LLM response: {e}")
        return EvaluatorResult(
            evaluator=evaluator_name,
            passed=False,
            score=0.0,
            feedback=f"Evaluator failed to parse LLM response. Raw: {raw[:300]}",
            status="failed"
        )
