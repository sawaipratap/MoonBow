import os
import argparse
from phase1.graph import phase1_graph
from phase1.dependencies import get_db_writer

def run(curriculum_file: str):
    print(f"Starting Phase 1 Processing for: {curriculum_file}")

    course_code_heuristic = os.path.splitext(os.path.basename(curriculum_file))[0]
    
    try:
        db_writer = get_db_writer()
        if db_writer.check_syllabus_exists(course_code_heuristic):
            print(f"Syllabus for {course_code_heuristic} already exists. Skipping.")
            return
    except NotImplementedError:
        print("MCP PostgreSQL not yet hooked up. Proceeding anyway.")

    # Initialize Graph State
    initial_state = {
        "curriculum_file_path": curriculum_file,
        "iteration_count": 0,
        "iteration_max": 3
    }

    # Execute Graph
    final_state = phase1_graph.invoke(initial_state)

    print("\n" + "="*50)
    print("PHASE 1 EXECUTION COMPLETE")
    print(f"Status: {final_state.get('phase_status', 'unknown')}")
    print(f"Iterations: {final_state.get('iteration_count')}")
    
    if final_state.get('phase_error'):
        print(f"Error: {final_state['phase_error']}")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 1 Syllabus Expansion")
    parser.add_argument(
        "file_path", 
        type=str, 
        nargs="?", 
        default="sample_curriculum.md",
        help="Path to the curriculum file"
    )
    
    args = parser.parse_args()
    run(args.file_path)
