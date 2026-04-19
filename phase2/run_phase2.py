import argparse
from phase2.graph import phase2_graph


def run(course_code: str):
    print(f"\n{'='*50}")
    print(f"Starting Phase 2 Evaluation for: {course_code}")
    print(f"{'='*50}\n")

    initial_state = {"course_code": course_code}
    final_state = phase2_graph.invoke(initial_state)

    print(f"\n{'='*50}")
    print("PHASE 2 EXECUTION COMPLETE")
    print(f"Status: {final_state.get('phase_status', 'unknown')}")

    if final_state.get("phase_status") == "passed":
        print("✓ All evaluators passed. Refined syllabus written to DB.")
    elif final_state.get("phase_status") == "returned_to_phase1":
        print("✗ Evaluation failed. Feedback for Phase 1:")
        print("-" * 40)
        print(final_state.get("compiled_feedback", ""))
    elif final_state.get("phase_error"):
        print(f"✗ Error: {final_state['phase_error']}")

    print(f"{'='*50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 2 Syllabus Evaluation")
    parser.add_argument(
        "course_code",
        type=str,
        help="Course code to evaluate (must have been processed by Phase 1 first)"
    )
    args = parser.parse_args()
    run(args.course_code)
