import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from phase2.state import Phase2State, EvaluatorResult
from phase2.config import config
from phase2.dependencies import get_ref_tool
from phase2.logger import log_llm_response
from phase2.nodes.level_evaluator import _parse_evaluator_response
import os


def _load_prompt() -> str:
    path = os.path.join(config.PROMPTS_DIR, "relevance_evaluator_prompt.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def relevance_evaluator_node(state: Phase2State) -> dict:
    domain = state.syllabus_draft.course_metadata.domain
    level = state.syllabus_draft.course_metadata.course_level

    # --- Reference DB Tool Call ---
    # Graceful degradation: if the reference DB is unavailable, mark as skipped
    benchmarks = {}
    standards = {}
    ref_available = True

    try:
        ref_tool = get_ref_tool()
        benchmarks = ref_tool.lookup_benchmark_curriculum(domain, level, top_k=3)
        standards = ref_tool.lookup_accreditation_standards(domain, level, accreditation_body="NBA")
    except (ConnectionError, LookupError, FileNotFoundError) as e:
        print(f"[relevance_evaluator] Reference DB unavailable ({e}). Marking as skipped.")
        ref_available = False
    except Exception as e:
        print(f"[relevance_evaluator] Unexpected error from ref DB ({e}). Marking as skipped.")
        ref_available = False

    if not ref_available:
        return {
            "relevance_eval_result": EvaluatorResult(
                evaluator="relevance",
                passed=True,
                score=0.0,
                feedback="Relevance evaluation skipped — reference DB unavailable. Manual review recommended.",
                status="skipped"
            )
        }

    # --- LLM Evaluation with Reference Data ---
    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.0,
        max_tokens=config.LLM_MAX_TOKENS
    )

    prompt_template = _load_prompt()
    prompt = prompt_template.format(
        domain=domain,
        level=level,
        syllabus_json=json.dumps(state.syllabus_draft.model_dump(), indent=2),
        benchmark_data=json.dumps(benchmarks, indent=2),
        standards_data=json.dumps(standards, indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    log_llm_response("relevance_evaluator", response.content)

    result = _parse_evaluator_response(response.content, "relevance")
    print(f"[relevance_evaluator] Result: {'PASS' if result.passed else 'FAIL'} "
          f"(score={result.score:.2f})")
    return {"relevance_eval_result": result}
