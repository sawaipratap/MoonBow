"""
run_pipeline.py — MoonBow Phase 1 + Phase 2 Orchestrator

This script is the macro-wrapper that:
  1. Runs Phase 1 (curriculum → syllabus expansion)
  2. Runs Phase 2 (parallel syllabus evaluation)
  3. If Phase 2 fails, it injects the compiled evaluator feedback back into
     Phase 1's Expander and re-runs the expansion loop.
  4. Repeats until Phase 2 passes or the max pipeline iterations are reached.

Run:
    PYTHONPATH=. python3 run_pipeline.py phase1/test_data/sample_curriculum.md
"""

import os
import argparse
import sys

# Shared max pipeline iterations (Phase 1 → Phase 2 → Phase 1 loop)
MAX_PIPELINE_ITERATIONS = int(os.getenv("MAX_PIPELINE_ITERATIONS", "2"))


def run_phase1(curriculum_file: str, extra_feedback: str = "") -> dict:
    """Run Phase 1. Optionally injects Phase 2 failure feedback into the initial expander context."""
    from phase1.graph import phase1_graph
    from phase1.state import Phase1State

    print(f"\n{'='*60}")
    print(f"PHASE 1: Syllabus Expansion")
    print(f"{'='*60}")

    initial_state = {
        "curriculum_file_path": curriculum_file,
        "iteration_count": 0,
        "iteration_max": 3,
    }

    if extra_feedback:
        # Inject Phase 2 feedback as initial critic context so the expander
        # sees it on its very first iteration without waiting for the Gap Critic.
        print("[pipeline] Injecting Phase 2 feedback into Phase 1 Expander context.")
        initial_state["expander_context"] = (
            "## Phase 2 Refinement Feedback (Address These Before Expanding)\n"
            f"{extra_feedback}\n"
        )

    final_state = phase1_graph.invoke(initial_state)

    status = final_state.get("phase_status", "unknown")
    print(f"\n[pipeline] Phase 1 complete. Status: {status}")
    return final_state


def run_phase2(phase1_final_state: dict) -> dict:
    """Run Phase 2 using the syllabus produced by Phase 1."""
    from phase2.graph import phase2_graph

    syllabus_draft = (
        phase1_final_state.get("syllabus_final")
        or phase1_final_state.get("syllabus_draft")
    )

    if not syllabus_draft:
        print("[pipeline] ERROR: Phase 1 produced no syllabus. Cannot run Phase 2.")
        return {"phase_status": "failed_unexpectedly", "aggregated_feedback": "Phase 1 produced no syllabus."}

    print(f"\n{'='*60}")
    print(f"PHASE 2: Syllabus Refinement")
    print(f"{'='*60}")

    initial_state = {"syllabus_draft": syllabus_draft}
    final_state = phase2_graph.invoke(initial_state)

    status = final_state.get("phase_status", "unknown")
    print(f"\n[pipeline] Phase 2 complete. Status: {status}")
    return final_state


def run_pipeline(curriculum_file: str):
    pipeline_iteration = 0
    phase2_feedback = ""   # feedback injected from Phase 2 → Phase 1

    while pipeline_iteration < MAX_PIPELINE_ITERATIONS:
        pipeline_iteration += 1
        print(f"\n{'#'*60}")
        print(f"# PIPELINE ITERATION {pipeline_iteration} / {MAX_PIPELINE_ITERATIONS}")
        print(f"{'#'*60}")

        # --- Run Phase 1 ---
        p1_state = run_phase1(curriculum_file, extra_feedback=phase2_feedback)

        p1_status = p1_state.get("phase_status", "failed")
        if p1_status == "failed":
            print(f"\n[pipeline] ABORT: Phase 1 failed unexpectedly. Error: {p1_state.get('phase_error')}")
            sys.exit(1)

        # --- Run Phase 2 ---
        p2_state = run_phase2(p1_state)

        p2_status = p2_state.get("phase_status", "unknown")

        if p2_status == "passed":
            print(f"\n{'#'*60}")
            print("# PIPELINE COMPLETE — SYLLABUS APPROVED")
            print(f"# Completed in {pipeline_iteration} pipeline iteration(s).")
            print(f"{'#'*60}")
            return p2_state

        elif p2_status == "failed_needs_phase1_rework":
            phase2_feedback = p2_state.get("aggregated_feedback", "")
            print(
                f"\n[pipeline] Phase 2 failed. Routing feedback back to Phase 1 "
                f"(iteration {pipeline_iteration + 1} of max {MAX_PIPELINE_ITERATIONS})."
            )
            if pipeline_iteration >= MAX_PIPELINE_ITERATIONS:
                print(
                    "\n[pipeline] WARNING: Max pipeline iterations reached. "
                    "Force-promoting syllabus to Phase 3 despite Phase 2 failures. "
                    "Manual review recommended."
                )
                return p2_state

        else:
            print(f"\n[pipeline] ABORT: Unexpected Phase 2 status: {p2_status}")
            sys.exit(1)

    return p2_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MoonBow Pipeline — Phase 1 + Phase 2 Orchestrator"
    )
    parser.add_argument(
        "curriculum_file",
        type=str,
        help="Path to the curriculum markdown file (e.g. phase1/test_data/sample_curriculum.md)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.curriculum_file):
        print(f"[pipeline] ERROR: Curriculum file not found: {args.curriculum_file}")
        sys.exit(1)

    run_pipeline(args.curriculum_file)
