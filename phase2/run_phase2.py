import argparse
from phase2.graph import phase2_graph
from phase2.dependencies import get_db_reader


def run(course_code: str):
    print(f"\nStarting Phase 2 Processing for course: {course_code}")
    print("="*50)

    # Load the Phase 1 syllabus for this course
    db_reader = get_db_reader()
    try:
        syllabus = db_reader.read_latest_syllabus(course_code)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return None

    # Initialize Phase 2 state
    initial_state = {
        "syllabus_draft": syllabus,
    }

    # Run the Phase 2 graph
    final_state = phase2_graph.invoke(initial_state)

    print("\n" + "="*50)
    print("PHASE 2 EXECUTION COMPLETE")
    print(f"Status: {final_state.get('phase_status', 'unknown')}")
    if final_state.get("aggregated_feedback"):
        print("\nFeedback for Phase 1 Expander:")
        print(final_state["aggregated_feedback"])
    print("="*50)

    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 2 Syllabus Refinement")
    parser.add_argument(
        "course_code",
        type=str,
        nargs="?",
        default="AUTO",
        help="Course code to process (used to find Phase 1 mock output). Defaults to latest."
    )
    args = parser.parse_args()
    run(args.course_code)
