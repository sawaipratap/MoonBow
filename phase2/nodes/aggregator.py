from phase2.state import Phase2State, EvaluationResult
from phase2.dependencies import get_db_writer


def aggregator_node(state: Phase2State) -> dict:
    """
    Fan-in node. Receives all 4 evaluator results and makes the final routing decision.
    - If ALL pass: status = "passed", write refined syllabus to DB.
    - If ANY fail: status = "failed_needs_phase1_rework", compile feedback for Phase 1.
    """
    evaluators = {
        "level": state.level_evaluation,
        "sequence": state.sequence_evaluation,
        "hours": state.hours_evaluation,
        "relevance": state.relevance_evaluation,
    }

    # Ensure all evaluators ran
    missing = [name for name, result in evaluators.items() if result is None]
    if missing:
        print(f"[aggregator] WARNING: Missing evaluation results from: {missing}. Treating as failed.")
        for name in missing:
            evaluators[name] = EvaluationResult(
                passed=False,
                feedback=f"[{name}_evaluator] Did not produce a result.",
                confidence_score=0.0
            )

    all_passed = all(r.passed for r in evaluators.values())

    # Print summary
    print("\n[aggregator] ====== Phase 2 Evaluation Summary ======")
    for name, result in evaluators.items():
        status_icon = "✓" if result.passed else "✗"
        print(f"  {status_icon} [{name}]: passed={result.passed} | confidence={result.confidence_score:.2f}")
        if not result.passed:
            print(f"      Feedback: {result.feedback}")
    print("=" * 50)

    # Compile aggregated feedback (only from failing evaluators)
    failing_feedback_parts = []
    for name, result in evaluators.items():
        if not result.passed:
            failing_feedback_parts.append(
                f"[{name.upper()} EVALUATOR FAILED]\n{result.feedback}"
            )

    aggregated_feedback = "\n\n".join(failing_feedback_parts) if failing_feedback_parts else ""

    if all_passed:
        phase_status = "passed"
        print("[aggregator] All evaluators passed. Syllabus approved for Phase 3.")

        # Persist the refined syllabus
        course_code = state.syllabus_draft.course_metadata.course_code
        try:
            db_writer = get_db_writer()
            record_id = db_writer.write_refined_syllabus(
                syllabus=state.syllabus_draft,
                course_code=course_code,
                phase_status=phase_status,
                evaluator_results={
                    name: {"passed": r.passed, "feedback": r.feedback, "confidence": r.confidence_score}
                    for name, r in evaluators.items()
                }
            )
            print(f"[aggregator] Refined syllabus written. Record ID: {record_id}")
        except Exception as e:
            print(f"[aggregator] Write failed: {e}. Continuing with in-memory result.")
    else:
        failing_names = [name for name, r in evaluators.items() if not r.passed]
        phase_status = "failed_needs_phase1_rework"
        print(f"[aggregator] Evaluation failed on: {failing_names}. Routing back to Phase 1 Expander.")

    return {
        "aggregated_feedback": aggregated_feedback,
        "phase_status": phase_status,
    }
