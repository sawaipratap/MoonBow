import json
from phase1.state import Phase1State, CourseMetadata
from phase1.dependencies import get_file_reader
from phase1.config import config
from phase1.logger import log_llm_response
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def curriculum_loader_node(state: Phase1State) -> dict:
    file_reader = get_file_reader()
    curriculum_text = file_reader.read_curriculum(state.curriculum_file_path)

    # Use LLM to extract structured metadata from raw text
    llm = ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL_NAME,
        temperature=0.0,    # deterministic for extraction tasks
        max_tokens=1024
    )

    extraction_prompt = f"""
Extract course metadata from this curriculum document. 
Return ONLY valid JSON with these exact fields, nothing else:

{{
  "course_name": "string",
  "course_code": "string",
  "course_level": "UG" or "PG" or "PhD",
  "credit_hours": integer,
  "domain": "string",
  "institution": "string",
  "semester": "string",
  "prerequisites": ["string"]
}}

Curriculum text:
{curriculum_text}
"""

    response = llm.invoke([HumanMessage(content=extraction_prompt)])
    log_llm_response("curriculum_loader", response.content)

    try:
        raw_output = response.content.strip()
        # robustly extract json by finding boundaries
        start = raw_output.find("{")
        end = raw_output.rfind("}")
        if start != -1 and end != -1:
            raw_output = raw_output[start:end+1]
            
        metadata_dict = json.loads(raw_output)
        course_metadata = CourseMetadata(**metadata_dict)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[curriculum_loader] Metadata extraction failed: {e}. Using minimal metadata.")
        course_metadata = CourseMetadata(
            course_name="Unknown",
            course_code="UNKNOWN",
            course_level="UG",
            credit_hours=3,
            domain="Unknown",
            institution="Unknown",
            semester="Unknown",
            prerequisites=[]
        )

    return {
        "curriculum_raw": curriculum_text,
        "course_metadata": course_metadata
    }
