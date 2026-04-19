import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from phase2.state import Phase2State, EvaluatorResult
from phase2.config import config
from phase2.logger import log_llm_response
from phase2.nodes.level_evaluator import _parse_evaluator_response
import os


def _load_prompt() -> str:
    path = os.path.join(config.PROMPTS_DIR, "sequence_evaluator_prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def sequence_evaluator_node(state: Phase2State) -> dict:
    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.0,
        max_tokens=config.LLM_MAX_TOKENS
    )

    prompt_template = _load_prompt()
    syllabus_json = json.dumps(state.syllabus_draft.model_dump(), indent=2)

    prompt = prompt_template.format(syllabus_json=syllabus_json)

    response = llm.invoke([HumanMessage(content=prompt)])
    log_llm_response("sequence_evaluator", response.content)

    result = _parse_evaluator_response(response.content, "sequence")
    print(f"[sequence_evaluator] Result: {'PASS' if result.passed else 'FAIL'} "
          f"(score={result.score:.2f})")
    return {"sequence_eval_result": result}
