from phase2.state import Phase2State
from phase2.dependencies import get_db_writer


def output_writer_node(state: Phase2State) -> dict:
    """
    Writes the approved refined syllabus + all evaluator results to the DB.
    Only runs after the aggregator confirms all evaluators passed.
    """
    evaluation_results = {
        "level": state.level_eval_result.model_dump() if state.level_eval_result else None,
        "sequence": state.sequence_eval_result.model_dump() if state.sequence_eval_result else None,
        "hours": state.hours_eval_result.model_dump() if state.hours_eval_result else None,
        "relevance": state.relevance_eval_result.model_dump() if state.relevance_eval_result else None,
    }

    db_writer = get_db_writer()
    record_id = db_writer.write_refined_syllabus(
        syllabus=state.syllabus_draft,
        course_code=state.course_code,
        evaluation_results=evaluation_results
    )
    print(f"[output_writer] Refined syllabus written for {state.course_code}: {record_id}")
    return {}
