import os
import json
from phase1.state import Phase1State, SyllabusDraft
from phase1.config import config
from phase1.logger import log_llm_response
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

def _load_prompt(prompt_file: str) -> str:
    prompt_path = os.path.join(config.PROMPTS_DIR, prompt_file)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def _build_expander_context(state: Phase1State) -> str:
    context_parts = []

    if state.course_metadata:
        context_parts.append(f"""
## Course Metadata
- Name: {state.course_metadata.course_name}
- Code: {state.course_metadata.course_code}
- Level: {state.course_metadata.course_level}
- Credit Hours: {state.course_metadata.credit_hours}
- Domain: {state.course_metadata.domain}
- Institution: {state.course_metadata.institution}
- Semester: {state.course_metadata.semester}
- Prerequisites: {', '.join(state.course_metadata.prerequisites) or 'None'}
""")

    context_parts.append(f"""
## Academic Level Calibrator Skill
{state.level_calibrator_skill}
""")

    context_parts.append(f"""
## Raw Curriculum
{state.curriculum_raw}
""")

    if state.critic_feedback and state.critic_feedback.has_gaps and state.iteration_count > 0:
        gaps_text = "\n".join([
            f"- [{g.gap_type}] At '{g.location}': {g.description}. Fix: {g.suggested_fix}"
            for g in state.critic_feedback.gaps
        ])
        context_parts.append(f"""
## Critic Feedback from Previous Iteration (Address These Specifically)
{state.critic_feedback.overall_assessment}

Specific gaps to fix:
{gaps_text}
""")

    if state.similar_topics_found:
        overlap_text = "\n".join([
            f"- '{r['topic']}' is covered in {r['course_name']} ({r['course_code']}) at {r['coverage_level']} level"
            for r in state.similar_topics_found
        ])
        context_parts.append(f"""
## Topics Already Covered in Prerequisite Courses (Avoid Duplication)
{overlap_text}
""")

    return "\n".join(context_parts)

def expander_node(state: Phase1State) -> dict:
    similar_topics = []

    # Note: Similarity Search tool logic will be implemented by the team in mcp/reference_database_mcp.
    # Currently passing empty similar topics.
    
    system_prompt = _load_prompt("expander_prompt.md")
    
    copy_state = state.model_copy()
    copy_state.similar_topics_found = similar_topics
    user_context = _build_expander_context(copy_state)

    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_context)
    ])
    log_llm_response("expander", response.content)

    raw_output = response.content.strip()

    # Robust extraction to bypass conversational filler and markdown
    start = raw_output.find("{")
    end = raw_output.rfind("}")
    if start != -1 and end != -1:
        raw_output = raw_output[start:end+1]

    try:
        syllabus_dict = json.loads(raw_output)
        syllabus_draft = SyllabusDraft(**syllabus_dict)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[expander] Failed to parse LLM output: {e}")
        return {
            "similar_topics_found": similar_topics
        }

    print(f"[expander] Iteration {state.iteration_count + 1}: Produced {len(syllabus_draft.topics)} units")

    return {
        "syllabus_draft": syllabus_draft,
        "similar_topics_found": similar_topics
    }
