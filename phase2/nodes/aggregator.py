from phase2.state import Phase2State, EvaluatorResult


def aggregator_node(state: Phase2State) -> dict:
    """
    Collects all four evaluator results and makes the routing decision.
    - All passed (or skipped) → phase_status = "passed"
    - Any failed → phase_status = "returned_to_phase1", with compiled feedback
    """
    results: list[EvaluatorResult] = [
        r for r in [
            state.level_eval_result,
            state.sequence_eval_result,
            state.hours_eval_result,
            state.relevance_eval_result,
        ] if r is not None
    ]

    failed = [r for r in results if r.status == "failed"]
    skipped = [r for r in results if r.status == "skipped"]
    passed = [r for r in results if r.status == "passed"]

    print(f"\n[aggregator] Results — "
          f"Passed: {len(passed)} | Failed: {len(failed)} | Skipped: {len(skipped)}")
    for r in results:
        mark = "✓" if r.passed else ("⚠" if r.status == "skipped" else "✗")
        print(f"  {mark} {r.evaluator:12s} score={r.score:.2f}  status={r.status}")

    if not failed:
        if skipped:
            print(f"[aggregator] {len(skipped)} evaluator(s) skipped — proceeding with conditional pass.")
        return {"phase_status": "passed"}

    # Compile targeted feedback for Phase 1 expander
    feedback_lines = [
        "## Phase 2 Evaluation Feedback\n"
        "The following evaluators failed. Address these specific issues in your revision:\n"
    ]
    for r in failed:
        feedback_lines.append(f"### {r.evaluator.upper()} EVALUATOR (score: {r.score:.2f})\n{r.feedback}\n")

    compiled = "\n".join(feedback_lines)
    print(f"[aggregator] {len(failed)} evaluator(s) failed. Returning to Phase 1.")
    return {
        "phase_status": "returned_to_phase1",
        "compiled_feedback": compiled
    }
