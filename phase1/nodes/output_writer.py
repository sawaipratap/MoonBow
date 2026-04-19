from phase1.state import Phase1State
from phase1.dependencies import get_db_writer

def output_writer_node(state: Phase1State) -> dict:
    if not state.syllabus_draft:
        return {
            "phase_status": "failed",
            "phase_error": "No syllabus draft available to write."
        }

    if state.critic_feedback and not state.critic_feedback.has_gaps:
        phase_status = "passed"
    else:
        phase_status = "force_passed"

    course_code = state.course_metadata.course_code if state.course_metadata else "UNKNOWN"

    try:
        db_writer = get_db_writer()
        record_id = db_writer.write_syllabus(
            syllabus=state.syllabus_draft,
            course_code=course_code,
            phase_status=phase_status,
            iteration_count=state.iteration_count
        )
        print(f"[output_writer] Syllabus written. Record ID: {record_id}. Status: {phase_status}")
    except Exception as e:
        return {
            "phase_status": "failed",
            "phase_error": str(e)
        }

    return {
        "syllabus_final": state.syllabus_draft,
        "phase_status": phase_status
    }
