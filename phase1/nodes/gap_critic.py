import os
import json
from phase1.state import Phase1State, CriticFeedback, CriticGap
from phase1.config import config
from phase1.logger import log_llm_response
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

def _load_prompt(prompt_file: str) -> str:
    prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def _build_critic_context(state: Phase1State) -> str:
    syllabus_json = json.dumps(
        state.syllabus_draft.model_dump(),
        indent=2
    ) if state.syllabus_draft else "No syllabus draft available."

    metadata_text = ""
    if state.course_metadata:
        metadata_text = f"""
## Course Metadata
- Name: {state.course_metadata.course_name}
- Level: {state.course_metadata.course_level}
- Credit Hours: {state.course_metadata.credit_hours}
- Domain: {state.course_metadata.domain}
- Prerequisites: {', '.join(state.course_metadata.prerequisites) or 'None'}
"""

    return f"""
{metadata_text}

## Academic Level Calibrator Skill
{state.level_calibrator_skill}

## Syllabus Draft to Evaluate
{syllabus_json}
"""

def gap_critic_node(state: Phase1State) -> dict:
    if not state.syllabus_draft:
        return {
            "critic_feedback": CriticFeedback(
                has_gaps=True,
                gaps=[CriticGap(
                    gap_type="coverage_gap",
                    location="entire syllabus",
                    description="No syllabus draft was produced by the expander.",
                    suggested_fix="Generate a complete syllabus expansion."
                )],
                overall_assessment="Expander failed to produce a syllabus.",
                confidence_score=1.0
            )
        }

    system_prompt = _load_prompt("gap_critic_prompt.md")
    user_context = _build_critic_context(state)

    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.1,    # low temperature for evaluation tasks
        max_tokens=2048
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_context)
    ])
    log_llm_response("gap_critic", response.content)

    try:
        raw_output = response.content.strip()
        start = raw_output.find("{")
        end = raw_output.rfind("}")
        if start != -1 and end != -1:
            raw_output = raw_output[start:end+1]

        feedback_dict = json.loads(raw_output)
        gaps = [CriticGap(**g) for g in feedback_dict.get("gaps", [])]
        critic_feedback = CriticFeedback(
            has_gaps=feedback_dict.get("has_gaps", False),
            gaps=gaps,
            overall_assessment=feedback_dict.get("overall_assessment", ""),
            confidence_score=feedback_dict.get("confidence_score", 0.5)
        )
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[gap_critic] Failed to parse critic output: {e}")
        critic_feedback = CriticFeedback(
            has_gaps=False,
            gaps=[],
            overall_assessment="Critic output could not be parsed. Passing through.",
            confidence_score=0.0
        )

    gap_count = len(critic_feedback.gaps)
    print(f"[gap_critic] Iteration {state.iteration_count + 1}: Found {gap_count} gaps. has_gaps={critic_feedback.has_gaps}")

    return {"critic_feedback": critic_feedback}
